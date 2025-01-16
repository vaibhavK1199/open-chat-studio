import React, {
  ChangeEvent,
  ChangeEventHandler,
  ReactNode,
  useId,
  useEffect,
} from "react";
import { useState } from "react";
import CodeMirror from '@uiw/react-codemirror';
import { python } from "@codemirror/lang-python";
import { githubLight, githubDark } from "@uiw/codemirror-theme-github";
import { CompletionContext, snippetCompletion as snip } from '@codemirror/autocomplete'
import { TypedOption } from "../types/nodeParameterValues";
import usePipelineStore from "../stores/pipelineStore";
import { classNames, concatenate, getCachedData, getSelectOptions } from "../utils";
import { NodeParams, PropertySchema } from "../types/nodeParams";
import { Node, useUpdateNodeInternals } from "reactflow";
import DOMPurify from 'dompurify';

export function getWidget(name: string) {
  switch (name) {
    case "toggle":
      return ToggleWidget
    case "float":
      return FloatWidget
    case "range":
      return RangeWidget
    case "expandable_text":
      return ExpandableTextWidget
    case "code":
      return CodeWidget
    case "select":
      return SelectWidget
    case "multiselect":
      return MultiSelectWidget
    case "llm_provider_model":
      return LlmWidget
    case "history":
      return HistoryTypeWidget
    case "keywords":
      return KeywordsWidget
    default:
      return DefaultWidget
  }
}

interface WidgetParams {
  nodeId: string;
  name: string;
  label: string;
  helpText: string;
  paramValue: string | string[];
  inputError: string | undefined;
  updateParamValue: (event: React.ChangeEvent<HTMLTextAreaElement | HTMLSelectElement | HTMLInputElement>) => any;
  schema: PropertySchema
  nodeParams: NodeParams
  required: boolean,
  getFieldError: (nodeId: string, fieldName: string) => string | undefined;
}

function DefaultWidget(props: WidgetParams) {
  return (
    <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
      <input
        className="input input-bordered w-full"
        name={props.name}
        onChange={props.updateParamValue}
        value={props.paramValue}
        type="text"
        required={props.required}
      ></input>
    </InputField>
  );
}

function FloatWidget(props: WidgetParams) {
  return <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
    <input
      className="input input-bordered w-full"
      name={props.name}
      onChange={props.updateParamValue}
      value={props.paramValue}
      type="number"
      step=".1"
      required={props.required}
    ></input>
  </InputField>
}

function RangeWidget(props: WidgetParams) {
  const getPropOrOther = (prop: string, other: string) => {
    const val = props.schema[prop];
    if (val !== undefined) {
      return val;
    }
    return props.schema[other];
  }
  return <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
    <input
      className="input input-bordered w-full input-sm"
      name={props.name}
      onChange={props.updateParamValue}
      value={props.paramValue}
      type="number"
      step=".1"
      required={props.required}
    ></input>
    <input
      className="range range-xs"
      name={props.name}
      onChange={props.updateParamValue}
      value={props.paramValue}
      type="range"
      min={getPropOrOther("minimum", "exclusiveMinimum")}
      max={getPropOrOther("maximum", "exclusiveMaximum")}
      step=".1"
      required={props.required}
    ></input>
  </InputField>
}

function ToggleWidget(props: WidgetParams) {
  const onChangeCallback = (event: React.ChangeEvent<HTMLInputElement>) => {
    event.target.value = event.target.checked ? "true" : "false";
    props.updateParamValue(event);
  };
  return (
    <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
      <input
        className="toggle"
        name={props.name}
        onChange={onChangeCallback}
        checked={props.paramValue === "true"}
        type="checkbox"
      ></input>
    </InputField>
  );
}

function SelectWidget(props: WidgetParams) {
  const options = getSelectOptions(props.schema);
  const selectedOption = options.find((option) => option.value.toString() === props.paramValue);
  const [link, setLink] = useState<string | undefined>(selectedOption?.edit_url);

  const onUpdate = (event: ChangeEvent<HTMLSelectElement>) => {
    const selectedOption = options.find((option) => option.value.toString() === event.target.value);
    setLink(selectedOption?.edit_url);
    props.updateParamValue(event);
  };


  return <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
    <div className="flex flex-row gap-2">
      <select
        className="select select-bordered w-full"
        name={props.name}
        onChange={onUpdate}
        value={props.paramValue}
        required={props.required}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {link && (
        <div className="tooltip" data-tip="Open in a new tab">
          <a target="_blank" href={DOMPurify.sanitize(link)} className="align-bottom hover:cursor-pointer">
            <i className="fa-solid fa-up-right-from-square fa-lg"></i>
          </a>
        </div>
      )}
    </div>
  </InputField>
}


function MultiSelectWidget(props: WidgetParams) {
  const options = getSelectOptions(props.schema);
  if (options.length == 0) {
    return <></>
  }
  let selectedValues = Array.isArray(props.paramValue) ? props.paramValue : [];

  const setNode = usePipelineStore((state) => state.setNode);

  function getNewNodeData(old: Node, updatedList: Array<string>) {
    return {
      ...old,
      data: {
        ...old.data,
        params: {
          ...old.data.params,
          [props.name]: updatedList,
        },
      },
    };
  }

  function onUpdate(event: ChangeEvent<HTMLInputElement>) {
    if (event.target.checked) {
      selectedValues.push(event.target.name)
    } else {
      selectedValues = selectedValues.filter((tool) => tool !== event.target.name)
    }
    setNode(props.nodeId, (old) => {
      return getNewNodeData(old, selectedValues);
    }
    );
  };

  return (
    <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
      {options.map((option) => (
        <div className="flex items-center mb-1" key={option.value}>
          <input
            className="checkbox"
            name={option.value}
            onChange={onUpdate}
            checked={selectedValues.includes(option.value)}
            id={option.value}
            key={option.value}
            type="checkbox"
          />
          <span className="ml-2">{option.label}</span>
        </div>
      ))}
    </InputField>
  )
}

export function CodeWidget(props: WidgetParams) {
  const [isDarkMode, setIsDarkMode] = useState(false);
  const setNode = usePipelineStore((state) => state.setNode);
  const onChangeCallback = (value: string) => {
    setNode(props.nodeId, (old) => ({
      ...old,
      data: {
        ...old.data,
        params: {
          ...old.data.params,
          [props.name]: value,
        },
      },
    }));
  };

    useEffect(() => {
        // Set dark / light mode
     const mediaQuery: MediaQueryList = window.matchMedia("(prefers-color-scheme: dark)");
     const handleChange = (event: MediaQueryListEvent): void => {
       setIsDarkMode(event.matches);
     };
    setIsDarkMode(mediaQuery.matches);

    mediaQuery.addEventListener("change", handleChange);
    return () => mediaQuery.removeEventListener("change", handleChange);
  }, []);

  const modalId = useId();
  const openModal = () => (document.getElementById(modalId) as HTMLDialogElement)?.showModal()
  const label = (
    <>
      {props.label}
      <div className="tooltip tooltip-left" data-tip={`Expand ${props.label}`}>
        <button className="btn btn-xs btn-ghost float-right" onClick={openModal}>
          <i className="fa-solid fa-expand-alt"></i>
        </button>
      </div >
    </>
  )
  return (
    <>
      <InputField label={label} help_text={props.helpText} inputError={props.inputError}>
        <div className="relative w-full">
          <textarea
            className="textarea textarea-bordered resize-none textarea-sm w-full overflow-x-auto overflow-y"
            disabled={true}
            rows={3}
            wrap="off"
            name={props.name}
            value={props.paramValue}
          ></textarea>
          <div
            className="absolute inset-0 cursor-pointer"
            onClick={openModal}
          ></div>
        </div>
      </InputField>
      <CodeModal
        modalId={modalId}
        humanName={props.label}
        value={concatenate(props.paramValue)}
        onChange={onChangeCallback}
        isDarkMode={isDarkMode}
        inputError={props.inputError}
      />
    </>
  );
}


export function CodeModal(
  { modalId, humanName, value, onChange, isDarkMode, inputError }: {
    modalId: string;
    humanName: string;
    value: string;
    onChange: (value: string) => void;
    isDarkMode: boolean;
    inputError: string | undefined;
  }) {
  const customCompletions = {
    get_participant_data: snip("get_participant_data()", {
      label: "get_participant_data",
      type: "keyword",
      detail: "Gets participant data for the current participant",
      boost: 1
    }),
    set_participant_data: snip("set_participant_data(${data})", {
      label: "set_participant_data",
      type: "keyword",
      detail: "Overwrites the participant data with the value provided",
      boost: 1
    }),
  }
  function pythonCompletions(context: CompletionContext) {
    const word = context.matchBefore(/\w*/)
    if (!word || (word.from == word.to && !context.explicit))
      return null
    return {
      from: word.from,
      options: Object.values(customCompletions).filter(completion =>
        completion.label.toLowerCase().startsWith(word.text.toLowerCase())
      )
    }
  }
  return (
    <dialog
      id={modalId}
      className="modal nopan nodelete nodrag noflow nowheel"
    >
      <div className="modal-box  min-w-[85vw] h-[80vh] flex flex-col">
        <form method="dialog">
          <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
            ✕
          </button>
        </form>
        <div className="flex-grow h-full w-full flex flex-col">
          <h4 className="mb-4 font-bold text-lg bottom-2 capitalize">
            {humanName}
          </h4>
          <CodeMirror
            value={value}
            onChange={onChange}
            className="textarea textarea-bordered h-full w-full flex-grow"
            height="100%"
            width="100%"
            theme={isDarkMode ? githubDark : githubLight}
            extensions={[
              python(),
              python().language.data.of({
                autocomplete: pythonCompletions
              })
            ]}
          />
        </div>
        <div className="flex flex-col">
            <span className="text-red-500">{inputError}</span>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        {/* Allows closing the modal by clicking outside of it */}
        <button>close</button>
      </form>
    </dialog>
  );
}



export function TextModal(
  {modalId, humanName, name, value, onChange}: {
    modalId: string;
    humanName: string;
    name: string;
    value: string | string[];
    onChange: ChangeEventHandler;
  }) {
  return (
    <dialog
      id={modalId}
      className="modal nopan nodelete nodrag noflow nowheel"
    >
      <div className="modal-box  min-w-[85vw] h-[80vh] flex flex-col">
        <form method="dialog">
          <button className="btn btn-sm btn-circle btn-ghost absolute right-2 top-2">
            ✕
          </button>
        </form>
        <div className="flex-grow h-full w-full flex flex-col">
          <h4 className="mb-4 font-bold text-lg bottom-2 capitalize">
            {humanName}
          </h4>
          <textarea
            className="textarea textarea-bordered textarea-lg w-full flex-grow resize-none"
            name={name}
            onChange={onChange}
            value={value}
          ></textarea>
        </div>
      </div>
      <form method="dialog" className="modal-backdrop">
        {/* Allows closing the modal by clicking outside of it */}
        <button>close</button>
      </form>
    </dialog>
  );
}

export function ExpandableTextWidget(props: WidgetParams) {
  const modalId = useId();
  const openModal = () => (document.getElementById(modalId) as HTMLDialogElement)?.showModal()
  const label = (
    <>{props.label}
      <div className="tooltip tooltip-left" data-tip={`Expand ${props.label}`}>
        <button className="btn btn-xs btn-ghost" onClick={openModal}>
          <i className="fa-solid fa-expand-alt"></i>
        </button>
      </div>
    </>
  )
  return (
    <InputField label={label} help_text={props.helpText} inputError={props.inputError}>
      <textarea
        className="textarea textarea-bordered resize-none textarea-sm w-full"
        rows={3}
        name={props.name}
        onChange={props.updateParamValue}
        value={props.paramValue}
      ></textarea>
      <TextModal
        modalId={modalId}
        humanName={props.label}
        name={props.name}
        value={props.paramValue}
        onChange={props.updateParamValue}>
      </TextModal>
    </InputField>
  );
}

export function KeywordsWidget(props: WidgetParams) {
  const setNode = usePipelineStore((state) => state.setNode);
  const setEdges = usePipelineStore((state) => state.setEdges);
  const updateNodeInternals = useUpdateNodeInternals()

  function getNewNodeData(old: Node, keywords: any[], numOutputs: number) {
    return {
      ...old,
      data: {
        ...old.data,
        params: {
          ...old.data.params,
          ["keywords"]: keywords,
          ["num_outputs"]: numOutputs,
        },
      },
    };
  }

  const addKeyword = () => {
    setNode(props.nodeId, (old) => {
      const updatedList = [...(old.data.params["keywords"] || []), ""];
      return getNewNodeData(old, updatedList, old.data.params.num_outputs + 1);
    });
    updateNodeInternals(props.nodeId);
  }

  const updateKeyword = (index: number, value: string) => {
    setNode(props.nodeId, (old) => {
        const updatedList = [...(old.data.params["keywords"] || [])];
        updatedList[index] = value;
        return getNewNodeData(old, updatedList, old.data.params.num_outputs);
      }
    );
  };

  const deleteKeyword = (index: number) => {
    setNode(props.nodeId, (old) => {
      const updatedList = [...(old.data.params["keywords"] || [])];
      updatedList.splice(index, 1);
      return getNewNodeData(old, updatedList, old.data.params.num_outputs - 1);
    });
    updateNodeInternals(props.nodeId);
    const handleName = `output_${index}`;
    setEdges((old) => {
      const edges = old.filter((edge) => {
        // remove edges that have this handle as source
        if (edge.source != props.nodeId) {
          return true;
        }
        return edge.sourceHandle != handleName;
      }).map((edge) => {
        // update sourceHandle of edges that have a sourceHandle greater than this index to preserve connections
        if (edge.source != props.nodeId) {
          return edge;
        }
        const sourceHandleIndex = edge.sourceHandle && +edge.sourceHandle.split("_")[1];
        if (sourceHandleIndex && sourceHandleIndex > index) {
          const newSourceHandle = `output_${sourceHandleIndex - 1}`;
          return {...edge, sourceHandle: newSourceHandle}
        }
        return edge;
      });
      return edges;
    });
  }

  const length = parseInt(concatenate(props.nodeParams.num_outputs)) || 1;
  const keywords = Array.isArray(props.nodeParams.keywords) ? props.nodeParams["keywords"] : []
  const canDelete = length > 1;
  return (
    <>
      <div className="form-control w-full capitalize">
        <label className="label font-bold">
          Outputs
          <div className="tooltip tooltip-left" data-tip="Add Keyword">
            <button className="btn btn-xs btn-ghost" onClick={() => addKeyword()}>
              <i className="fa-solid fa-plus"></i>
            </button>
          </div>
        </label>
        <small className="text-red-500">{props.inputError}</small>
      </div>
      <div className="ml-2">
        {Array.from({length: length}, (_, index) => {
          const value = keywords ? keywords[index] || "" : "";
          const label = `Output Keyword ${index + 1}`;
          return (
            <div className="form-control w-full capitalize" key={index}>
              <div className="flex justify-between items-center">
                <label className="label">{label}</label>
                <div className="tooltip tooltip-left" data-tip={`Delete Keyword ${index + 1}`}>
                  <button className="btn btn-xs btn-ghost" onClick={() => deleteKeyword(index)} disabled={!canDelete}>
                    <i className="fa-solid fa-minus"></i>
                  </button>
                </div>
              </div>
              <input
                className={classNames("input input-bordered w-full", value ? "" : "input-error")}
                name="keywords"
                onChange={(event) => updateKeyword(index, event.target.value)}
                value={value}
              ></input>
            </div>
          );
        })}
      </div>
    </>
  );
}

export function LlmWidget(props: WidgetParams) {

  const {parameterValues} = getCachedData();
  const setNode = usePipelineStore((state) => state.setNode);
  const updateParamValue = (event: ChangeEvent<HTMLSelectElement>) => {
    const {value} = event.target;
    const [providerId, providerModelId] = value.split('|:|');
    setNode(props.nodeId, (old) => ({
      ...old,
      data: {
        ...old.data,
        params: {
          ...old.data.params,
          llm_provider_id: providerId,
          llm_provider_model_id: providerModelId,
        },
      },
    }));
  };

  const makeValue = (providerId: string, providerModelId: string) => {
    return providerId + '|:|' + providerModelId;
  };

  type ProviderModelsByType = { [type: string]: TypedOption[] };
  const providerModelsByType = parameterValues.LlmProviderModelId.reduce((acc, provModel) => {
    if (!acc[provModel.type]) {
      acc[provModel.type] = [];
    }
    acc[provModel.type].push(provModel);
    return acc;
  }, {} as ProviderModelsByType);

  const providerId = concatenate(props.nodeParams.llm_provider_id);
  const providerModelId = concatenate(props.nodeParams.llm_provider_model_id);
  const value = makeValue(providerId, providerModelId)
  return (
    <InputField label={props.label} help_text={props.helpText} inputError={props.inputError}>
      <select
        className="select select-bordered w-full"
        name={props.name}
        onChange={updateParamValue}
        value={value}
      >
        <option value="" disabled>
          Select a model
        </option>
        {parameterValues.LlmProviderId.map((provider) => (
          providerModelsByType[provider.type] &&
          providerModelsByType[provider.type].map((providerModel) => (
            <option key={provider.value + providerModel.value} value={makeValue(provider.value, providerModel.value)}>
              {providerModel.label}
            </option>
          ))
        ))}
      </select>
    </InputField>
  );
}

export function HistoryTypeWidget(props: WidgetParams) {
  const options = getSelectOptions(props.schema);
  const historyType = concatenate(props.paramValue);
  const historyName = concatenate(props.nodeParams["history_name"]);
  const historyNameError = props.getFieldError(props.nodeId, "history_name");
  return (
    <>
      <div className="flex join">
        <InputField label="History" help_text={props.helpText}>
          <select
            className="select select-bordered join-item"
            name={props.name}
            onChange={props.updateParamValue}
            value={historyType}
          >
            {options.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </InputField>
        {historyType == "named" && (
          <InputField label="History Name" help_text={props.helpText}>
            <input
              className="input input-bordered join-item"
              name="history_name"
              onChange={props.updateParamValue}
              value={historyName || ""}
            ></input>
          </InputField>
        )}
      </div>
      <div className="flex flex-col">
        <small className="text-red-500">{historyNameError}</small>
      </div>
    </>
  )
    ;
}

export function InputField({label, help_text, inputError, children}: React.PropsWithChildren<{
  label: string | ReactNode,
  help_text: string,
  inputError?: string | undefined
}>) {
  return (
    <>
      <div className="form-control w-full capitalize">
        <label className="label font-bold">{label}</label>
        {children}
      </div>
      <div className="flex flex-col">
        <small className="text-red-500">{inputError}</small>
        <small className="text-muted">{help_text}</small>
      </div>
    </>
  );
}
