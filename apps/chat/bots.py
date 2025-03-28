import textwrap
from typing import TYPE_CHECKING, Any

from langchain.memory import ConversationBufferMemory
from langchain_core.language_models import BaseChatModel
from langchain_core.runnables import chain
from pydantic import ValidationError

from apps.annotations.models import TagCategories
from apps.chat.conversation import BasicConversation, Conversation
from apps.chat.exceptions import ChatException
from apps.chat.models import ChatMessageType
from apps.events.models import StaticTriggerType
from apps.events.tasks import enqueue_static_triggers
from apps.experiments.models import Experiment, ExperimentRoute, ExperimentSession, SafetyLayer
from apps.pipelines.nodes.base import PipelineState
from apps.service_providers.llm_service.default_models import get_default_model
from apps.service_providers.llm_service.prompt_context import PromptTemplateContext
from apps.service_providers.llm_service.runnables import create_experiment_runnable

if TYPE_CHECKING:
    from apps.channels.datamodels import Attachment


def create_conversation(
    prompt_str: str,
    source_material: str,
    llm: BaseChatModel,
) -> Conversation:
    try:
        return BasicConversation(
            prompt_str=prompt_str,
            source_material=source_material,
            memory=ConversationBufferMemory(return_messages=True),
            llm=llm,
        )
    except ValidationError as e:
        raise ChatException(str(e)) from e


def notify_users_of_violation(session_id: int, safety_layer_id: int):
    from apps.chat.tasks import notify_users_of_safety_violations_task

    notify_users_of_safety_violations_task.delay(session_id, safety_layer_id)


def get_bot(session: ExperimentSession, experiment: Experiment | None = None, disable_tools: bool = False):
    experiment = experiment or session.experiment_version
    if experiment.pipeline_id:
        return PipelineBot(session, experiment=experiment, disable_reminder_tools=disable_tools)
    return TopicBot(session, experiment, disable_tools=disable_tools)


class TopicBot:
    """
    Parameters
    ----------
    session:
        The session to provide the chat history. New messages will be saved to this session.
    experiment: (optional)
        The experiment to provide the source material and other data for the LLM.
        NOTE: Only use this if you know what you are doing. Normally this should be left empty, in which case
        the session's own experiment will be used. This is used in a multi-bot setup where the user might want
        a specific bot to handle a scheduled message, in which case it would be useful for the LLM to have the
        conversation history of the participant's chat with the router / main bot.
    """

    def __init__(self, session: ExperimentSession, experiment: Experiment | None = None, disable_tools: bool = False):
        self.experiment = experiment or session.experiment_version
        self.disable_tools = disable_tools
        self.prompt = self.experiment.prompt_text
        self.input_formatter = self.experiment.input_formatter
        self.llm = self.experiment.get_chat_model()
        self.source_material = self.experiment.source_material.material if self.experiment.source_material else None
        self.safety_layers = self.experiment.safety_layers.all()
        self.chat = session.chat
        self.session = session
        self.max_token_limit = self.experiment.max_token_limit
        self.input_tokens = 0
        self.output_tokens = 0

        # maps keywords to child experiments.
        self.child_experiment_routes = (
            ExperimentRoute.objects.select_related("child").filter(parent=self.experiment, type="processor").all()
        )
        self.child_chains = {}
        self.default_child_chain = None
        self.default_tag = None
        self.terminal_chain = None
        self.processor_experiment = None
        self.trace_service = self.experiment.trace_service

        # The chain that generated the AI message
        self.generator_chain = None
        self._initialize()

    def _initialize(self):
        for child_route in self.child_experiment_routes:
            child_runnable = create_experiment_runnable(
                child_route.child, self.session, self.disable_tools, trace_service=self.trace_service
            )
            self.child_chains[child_route.keyword.lower().strip()] = child_runnable
            if child_route.is_default:
                self.default_child_chain = child_runnable
                self.default_tag = child_route.keyword.lower().strip()

        if self.child_chains and not self.default_child_chain:
            self.default_tag, self.default_child_chain = list(self.child_chains.items())[0]

        self.chain = create_experiment_runnable(
            self.experiment, self.session, self.disable_tools, trace_service=self.trace_service
        )

        terminal_route = (
            ExperimentRoute.objects.select_related("child").filter(parent=self.experiment, type="terminal").first()
        )
        if terminal_route:
            self.terminal_chain = create_experiment_runnable(
                terminal_route.child, self.session, trace_service=self.trace_service
            )

        # load up the safety bots. They should not be agents. We don't want them using tools (for now)
        self.safety_bots = [
            SafetyBot(safety_layer, self.llm, self.source_material) for safety_layer in self.safety_layers
        ]

    def _call_predict(self, input_str, save_input_to_history=True, attachments: list["Attachment"] | None = None):
        if self.child_chains:
            tag, chain = self._get_child_chain(input_str, attachments)
        else:
            tag, chain = None, self.chain

        # The processor_experiment is the experiment that generated the output
        self.processor_experiment = chain.experiment
        result = chain.invoke(
            input_str,
            config={
                "configurable": {
                    "save_input_to_history": save_input_to_history,
                    "save_output_to_history": self.terminal_chain is None,
                    "experiment_tag": tag,
                }
            },
            attachments=attachments,
        )

        if self.terminal_chain:
            chain = self.terminal_chain
            result = chain.invoke(
                result.output,
                config={
                    "run_name": "terminal_chain",
                    "configurable": {
                        "save_input_to_history": False,
                        "experiment_tag": tag,
                        "include_conversation_history": False,
                    },
                },
            )

        self.generator_chain = chain

        enqueue_static_triggers.delay(self.session.id, StaticTriggerType.NEW_BOT_MESSAGE)
        self.input_tokens = self.input_tokens + result.prompt_tokens
        self.output_tokens = self.output_tokens + result.completion_tokens
        return result.output

    def _get_child_chain(self, input_str: str, attachments: list["Attachment"] | None = None) -> tuple[str, Any]:
        result = self.chain.invoke(
            input_str,
            config={
                "run_name": "get_child_chain",
                "configurable": {
                    "save_input_to_history": False,
                    "save_output_to_history": False,
                },
            },
            attachments=attachments,
        )
        self.input_tokens = self.input_tokens + result.prompt_tokens
        self.output_tokens = self.output_tokens + result.completion_tokens

        keyword = result.output.lower().strip()
        try:
            return keyword, self.child_chains[keyword]
        except KeyError:
            return self.default_tag, self.default_child_chain

    def process_input(self, user_input: str, save_input_to_history=True, attachments: list["Attachment"] | None = None):
        @chain
        def main_bot_chain(user_input):
            # human safety layers
            for safety_bot in self.safety_bots:
                if safety_bot.filter_human_messages() and not safety_bot.is_safe(user_input):
                    self._save_message_to_history(user_input, ChatMessageType.HUMAN)
                    enqueue_static_triggers.delay(self.session.id, StaticTriggerType.HUMAN_SAFETY_LAYER_TRIGGERED)
                    notify_users_of_violation(self.session.id, safety_layer_id=safety_bot.safety_layer.id)
                    return self._get_safe_response(safety_bot.safety_layer)

            response = self._call_predict(
                user_input, save_input_to_history=save_input_to_history, attachments=attachments
            )

            # ai safety layers
            for safety_bot in self.safety_bots:
                if safety_bot.filter_ai_messages() and not safety_bot.is_safe(response):
                    enqueue_static_triggers.delay(self.session.id, StaticTriggerType.BOT_SAFETY_LAYER_TRIGGERED)
                    return self._get_safe_response(safety_bot.safety_layer)

            return response

        config = {}
        if self.trace_service:
            callback = self.trace_service.get_callback(
                trace_name=self.experiment.name,
                participant_id=str(self.session.participant.identifier),
                session_id=str(self.session.external_id),
            )
            config = {
                "run_name": self.experiment.name,
                "callbacks": [callback],
                "metadata": {
                    "participant-id": str(self.session.participant.identifier),
                    "session-id": str(self.session.external_id),
                },
            }

        try:
            return main_bot_chain.invoke(user_input, config=config)
        finally:
            if self.trace_service:
                self.trace_service.end()

    def get_ai_message_id(self) -> int | None:
        """Returns the generated AI message's ID. The caller can use this to fetch more information on this message"""
        if self.generator_chain and self.generator_chain.history_manager.ai_message:
            return self.generator_chain.history_manager.ai_message.id

    def _get_safe_response(self, safety_layer: SafetyLayer):
        if safety_layer.prompt_to_bot:
            bot_response = self._call_predict(safety_layer.prompt_to_bot, save_input_to_history=False)
        else:
            no_answer = "Sorry, I can't answer that. Please try something else."
            bot_response = safety_layer.default_response_to_user or no_answer
            # This is a bit of a hack to store the bot's response, since it didn't really generate it, but we still
            # need to save it
            self._save_message_to_history(bot_response, ChatMessageType.AI)
            self.generator_chain = self.chain

        if self.generator_chain and self.generator_chain.history_manager.ai_message:
            self.generator_chain.history_manager.ai_message.add_system_tag(
                safety_layer.name, tag_category=TagCategories.SAFETY_LAYER_RESPONSE
            )
        return bot_response

    def _save_message_to_history(self, message: str, message_type: ChatMessageType):
        self.chain.history_manager.save_message_to_history(message, type_=message_type)


class SafetyBot:
    def __init__(self, safety_layer: SafetyLayer, llm: BaseChatModel, source_material: str | None):
        self.safety_layer = safety_layer
        self.prompt = safety_layer.prompt_text
        self.llm = llm
        self.source_material = source_material
        self.input_tokens = 0
        self.output_tokens = 0
        self._initialize()

    def _initialize(self):
        self.conversation = create_conversation(self.prompt, self.source_material, self.llm)

    def _call_predict(self, input_str):
        response, prompt_tokens, completion_tokens = self.conversation.predict(input=input_str)
        self.input_tokens = self.input_tokens + prompt_tokens
        self.output_tokens = self.output_tokens + completion_tokens
        return response

    def is_safe(self, input_str: str) -> bool:
        result = self._call_predict(input_str)
        if result.strip().lower().startswith("safe"):
            return True
        elif result.strip().lower().startswith("unsafe"):
            return False
        else:
            return False

    def filter_human_messages(self) -> bool:
        return self.safety_layer.messages_to_review == "human"

    def filter_ai_messages(self) -> bool:
        return self.safety_layer.messages_to_review == "ai"


class PipelineBot:
    def __init__(self, session: ExperimentSession, experiment: Experiment, disable_reminder_tools=False):
        self.experiment = experiment
        self.session = session
        self.ai_message_id = None
        self.disable_reminder_tools = disable_reminder_tools

    def process_input(self, user_input: str, save_input_to_history=True, attachments: list["Attachment"] | None = None):
        attachments = attachments or []
        serializable_attachments = [attachment.model_dump() for attachment in attachments]
        output: PipelineState = self.experiment.pipeline.invoke(
            PipelineState(
                messages=[user_input],
                experiment_session=self.session,
                attachments=serializable_attachments,
                pipeline_version=self.experiment.pipeline.version_number,
            ),
            self.session,
            save_input_to_history=save_input_to_history,
            disable_reminder_tools=self.disable_reminder_tools,
        )
        self.ai_message_id = output["ai_message_id"]
        return output["messages"][-1]

    def get_ai_message_id(self) -> int:
        return self.ai_message_id


class EventBot:
    SYSTEM_PROMPT = textwrap.dedent(
        """
    Your role is to generate messages to send to users. These could be reminders
    or prompts to help them complete their tasks. The text that you generate will be sent
    to the user in a chat message.

    You should generate the message in the language of the user.

    This is the data we have about the user:
    ```
    {participant_data}
    ```

    The current date and time is: {current_datetime}
    
    Here are the most recent messages in the conversation:
    ```
    {conversation_history}
    ```
    """
    )

    def __init__(self, session: ExperimentSession, experiment: Experiment):
        self.session = session
        self.experiment = experiment or session.experiment_version

    def get_user_message(self, event_prompt: str):
        provider = self.llm_provider
        if not provider:
            raise Exception("No LLM provider found")

        model = get_default_model(provider.type)

        service = provider.get_llm_service()
        llm = service.get_chat_model(model.name, 0.7)
        response = llm.invoke(
            [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": f"Generate the message for the user based on this text: {event_prompt}"},
            ]
        )
        return response.content

    @property
    def llm_provider(self):
        if self.experiment.llm_provider:
            return self.experiment.llm_provider

        # If no LLM provider is set, use the first one in the team
        return self.experiment.team.llmprovider_set.first()

    @property
    def system_prompt(self):
        context = PromptTemplateContext(self.session, None).get_context(["participant_data", "current_datetime"])
        context["conversation_history"] = self.get_conversation_history()
        return self.SYSTEM_PROMPT.format(**context)

    def get_conversation_history(self):
        messages = []
        for message in self.session.chat.message_iterator(with_summaries=False):
            messages.append(f"{message.role}: {message.content}")
            if len(messages) > 10:
                break
        return "\n".join(reversed(messages))
