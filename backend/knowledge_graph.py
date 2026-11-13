"""Atlas AI Gen-4 — Knowledge Connections Graph.

Constructs and traverses an interconnected semantic graph across:
- Research concepts
- Uploaded datasets & schemas
- Model architectures & checkpoints
- Experimental findings
- Supporting and contradictory citations
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set


class RelationType:
    SUPPORTS = "SUPPORTS"
    CONTRADICTS = "CONTRADICTS"
    EVALUATES_ON = "EVALUATES_ON"
    SUPERSEDES = "SUPERSEDES"
    DERIVED_FROM = "DERIVED_FROM"
    CAUTION_LEAKAGE = "CAUTION_LEAKAGE"
    CORRELATES_WITH = "CORRELATES_WITH"


@dataclass
class KnowledgeNode:
    id: str
    label: str
    node_type: str  # "CONCEPT" | "DATASET" | "MODEL" | "EXPERIMENT" | "PAPER"
    properties: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class KnowledgeEdge:
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    evidence_id: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class KnowledgeConnectionsGraph:
    """Multi-source knowledge graph for Atlas research."""

    def __init__(self):
        self.nodes: Dict[str, KnowledgeNode] = {}
        self.edges: List[KnowledgeEdge] = []
        self._adjacency: Dict[str, List[KnowledgeEdge]] = {}

    def add_node(self, node_id: str, label: str, node_type: str, properties: Optional[Dict[str, Any]] = None) -> KnowledgeNode:
        if node_id in self.nodes:
            self.nodes[node_id].label = label
            if properties:
                self.nodes[node_id].properties.update(properties)
            return self.nodes[node_id]

        node = KnowledgeNode(id=node_id, label=label, node_type=node_type, properties=properties or {})
        self.nodes[node_id] = node
        self._adjacency.setdefault(node_id, [])
        return node

    def add_edge(self, source_id: str, target_id: str, relation: str, weight: float = 1.0, evidence_id: Optional[str] = None) -> KnowledgeEdge:
        edge = KnowledgeEdge(source_id=source_id, target_id=target_id, relation=relation, weight=weight, evidence_id=evidence_id)
        self.edges.append(edge)
        self._adjacency.setdefault(source_id, []).append(edge)
        return edge

    def get_related_nodes(self, node_id: str, relation: Optional[str] = None) -> List[Tuple[KnowledgeNode, KnowledgeEdge]]:
        edges = self._adjacency.get(node_id, [])
        results = []
        for e in edges:
            if relation is None or e.relation == relation:
                target = self.nodes.get(e.target_id)
                if target:
                    results.append((target, e))
        return results

    def find_contradictions(self) -> List[Dict[str, Any]]:
        """Identify all explicitly flagged contradictory links in the knowledge graph."""
        contradictions = []
        for e in self.edges:
            if e.relation == RelationType.CONTRADICTS:
                src = self.nodes.get(e.source_id)
                tgt = self.nodes.get(e.target_id)
                if src and tgt:
                    contradictions.append({
                        "source": src.label,
                        "source_type": src.node_type,
                        "target": tgt.label,
                        "target_type": tgt.node_type,
                        "evidence_id": e.evidence_id,
                    })
        return contradictions

    def export_graph_summary(self) -> Dict[str, Any]:
        return {
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "node_types": list(set(n.node_type for n in self.nodes.values())),
            "relation_types": list(set(e.relation for e in self.edges)),
        }


# Global singleton instance
knowledge_graph = KnowledgeConnectionsGraph()
