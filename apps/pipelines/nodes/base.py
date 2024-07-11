from abc import ABC
from collections.abc import Callable, Sequence
from functools import cached_property
from typing import Annotated, Any, TypedDict

from langchain_core.runnables import RunnableConfig
from pydantic import BaseModel
from pydantic_core import ValidationError

from apps.experiments.models import ExperimentSession
from apps.pipelines.exceptions import PipelineNodeBuildError
from apps.pipelines.graph import Node
from apps.pipelines.logging import PipelineLoggingCallbackHandler


def add_messages(left: list, right: list):
    # Could probably log here
    return left + right


class PipelineState(TypedDict):
    messages: Annotated[Sequence[Any], add_messages]
    experiment_session: ExperimentSession


class PipelineNode(BaseModel, ABC):
    """Pipeline node that implements the `_process` method and returns a new state. Define required parameters as
    typed fields.

    Example:
        class FunNode(PipelineNode):
            required_parameter_1: CustomType
            optional_parameter_1: Optional[CustomType] = None

            def _process(self, state: PipelineState) -> PipelineState:
                input = state["messages"][-1]
                output = ... # do something
                return output # The state will be updated with output

       class FunLambdaNode(PipelineNode):
            required_parameter_1: str

            def _process(self, state: PipelineState) -> PipelineState:
                ...
                return # The state will not be updated, since None is returned

    """

    config: RunnableConfig | None = None

    class Config:
        arbitrary_types_allowed = True

    @classmethod
    def build(cls, node: Node) -> Callable[[dict], dict]:
        try:
            return cls(**node.params)
        except ValidationError as ex:
            raise PipelineNodeBuildError(ex)

    def process(self, state: PipelineState, config) -> PipelineState:
        self.config = config
        cls_name = self.__class__.__name__
        self.logger.info(f"{cls_name} starting")

        output = self._process(state)

        self.logger.info(f"{cls_name} finished with output: {output}")

        # Append the output to the state, otherwise do not change the state
        return PipelineState(messages=[output]) if output else PipelineState()

    def _process(self, state: PipelineState) -> PipelineState:
        """The method that executes node specific functionality"""
        raise NotImplementedError

    @cached_property
    def logger(self):
        for handler in self.config["callbacks"].handlers:
            if isinstance(handler, PipelineLoggingCallbackHandler):
                return handler.logger
