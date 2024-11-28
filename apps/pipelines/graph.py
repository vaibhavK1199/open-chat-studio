from collections import defaultdict
from functools import cached_property, partial
from typing import Self

import pydantic
from langgraph.graph import StateGraph
from langgraph.graph.state import CompiledStateGraph
from pydantic_core import ValidationError

from apps.pipelines.const import STANDARD_OUTPUT_NAME
from apps.pipelines.exceptions import PipelineBuildError, PipelineNodeBuildError
from apps.pipelines.models import Pipeline
from apps.pipelines.nodes.nodes import EndNode, StartNode


class Node(pydantic.BaseModel):
    id: str
    label: str
    type: str
    params: dict = {}

    @property
    def pipeline_node_class(self):
        from apps.pipelines.nodes import nodes

        return getattr(nodes, self.type)

    @property
    def pipeline_node_instance(self):
        return self.pipeline_node_class(**self.params)


class Edge(pydantic.BaseModel):
    id: str
    source: str
    target: str
    sourceHandle: str | None = STANDARD_OUTPUT_NAME

    def is_conditional(self):
        return self.sourceHandle != STANDARD_OUTPUT_NAME


class PipelineGraph(pydantic.BaseModel):
    nodes: list[Node]
    edges: list[Edge]

    @cached_property
    def nodes_by_id(self) -> dict[str, Node]:
        return {node.id: node for node in self.nodes}

    @cached_property
    def conditional_edges(self) -> list[Edge]:
        return [edge for edge in self.edges if edge.is_conditional()]

    @cached_property
    def start_node(self) -> Node:
        start_nodes = [node for node in self.nodes if node.type == StartNode.__name__]
        return start_nodes[0]

    @cached_property
    def end_node(self) -> Node:
        end_nodes = [node for node in self.nodes if node.type == EndNode.__name__]
        return end_nodes[0]

    @cached_property
    def conditional_edge_map(self) -> dict[str, dict[str, str]]:
        conditional_edge_map = defaultdict(dict)
        for edge in self.conditional_edges:
            source_node = self.nodes_by_id[edge.source].pipeline_node_instance
            output_map = source_node.get_output_map()
            # this creates a map of the form:
            # {source_node: {'source_handle_1': value_to_follow_edge_1, 'source_handle_2': value_to_follow_edge_2}}
            conditional_edge_map[edge.source][output_map[edge.sourceHandle]] = edge.target
        return conditional_edge_map

    @cached_property
    def unconditional_edges(self) -> list[Edge]:
        return [edge for edge in self.edges if not edge.is_conditional()]

    @classmethod
    def build_runnable_from_pipeline(cls, pipeline: Pipeline) -> CompiledStateGraph:
        return cls.build_from_pipeline(pipeline).build_runnable()

    @classmethod
    def build_from_pipeline(cls, pipeline: Pipeline) -> Self:
        node_data = [
            Node(id=node.flow_id, label=node.label, type=node.type, params=node.params)
            for node in pipeline.node_set.all()
        ]
        edge_data = [Edge(**edge) for edge in pipeline.data["edges"]]
        return cls(nodes=node_data, edges=edge_data)

    def build_runnable(self) -> CompiledStateGraph:
        from apps.pipelines.nodes.base import PipelineState

        if not self.nodes:
            raise PipelineBuildError("There are no nodes in the graph")

        self._validate_start_end_nodes()

        state_graph = StateGraph(PipelineState)

        self._add_nodes_to_graph(state_graph)
        self._add_edges_to_graph(state_graph)

        state_graph.set_entry_point(self.start_node.id)
        state_graph.set_finish_point(self.end_node.id)

        compiled_graph = state_graph.compile()
        # compiled_graph.get_graph().print_ascii()
        return compiled_graph

    def _add_nodes_to_graph(self, state_graph):
        try:
            for node in self.nodes:
                incoming_edges = [edge.source for edge in self.edges if edge.target == node.id]
                state_graph.add_node(node.id, partial(node.pipeline_node_instance.process, node.id, incoming_edges))
        except ValidationError as ex:
            raise PipelineNodeBuildError(ex)

    def _add_edges_to_graph(self, state_graph):
        seen_sources = set()
        for edge in self.conditional_edges:
            if edge.source not in seen_sources:  # We only add edges from the same source once
                node_instance = self.nodes_by_id[edge.source].pipeline_node_instance
                state_graph.add_conditional_edges(
                    edge.source,
                    partial(node_instance.process_conditional, node_id=edge.source),
                    self.conditional_edge_map[edge.source],
                )
            seen_sources.add(edge.source)

        for edge in self.unconditional_edges:
            state_graph.add_edge(edge.source, edge.target)

    def _validate_start_end_nodes(self):
        start_nodes = [node for node in self.nodes if node.type == StartNode.__name__]
        if len(start_nodes) != 1:
            raise PipelineBuildError(
                f"There should be exactly 1 {StartNode.model_config['json_schema_extra'].label} node"
            )
        end_nodes = [node for node in self.nodes if node.type == EndNode.__name__]
        if len(end_nodes) != 1:
            raise PipelineBuildError(
                f"There should be exactly 1 {EndNode.model_config['json_schema_extra'].label} node"
            )
