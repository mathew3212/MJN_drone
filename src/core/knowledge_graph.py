"""
Persistent Knowledge Graph
============================
A structured knowledge base describing:

  - Environment (terrain, zones, corridors)
  - Objects (buildings, obstacles, vehicles)
  - Missions (history, patterns, outcomes)
  - Weather (patterns, predictions)
  - Risk regions (computed from experience)
  - Safe corridors (learned from flights)
  - Charging stations (locations, availability)
  - Previous experiences (lessons learned)

The AI reasons using relationships instead of isolated data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict
import time


@dataclass
class Node:
    """A node in the knowledge graph."""
    node_id: str
    node_type: str
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0
    last_updated: float = field(default_factory=time.time)
    access_count: int = 0


@dataclass
class Edge:
    """A relationship between nodes."""
    source_id: str
    target_id: str
    relation: str
    weight: float = 1.0
    properties: Dict[str, Any] = field(default_factory=dict)
    confidence: float = 1.0


class KnowledgeGraph:
    """
    Persistent knowledge graph for the autonomous system.
    
    Supports:
      - Adding/removing nodes and edges
      - Querying by type, relation, or properties
      - Confidence-weighted queries
      - Path finding between nodes
      - Subgraph extraction
      - Statistics
    """

    def __init__(self):
        self.nodes: Dict[str, Node] = {}
        self.edges: List[Edge] = []
        self._adjacency: Dict[str, List[Edge]] = defaultdict(list)
        self._reverse_adjacency: Dict[str, List[Edge]] = defaultdict(list)

    def add_node(self, node_id: str, node_type: str,
                 properties: Dict = None, confidence: float = 1.0):
        """Add a node to the graph."""
        node = Node(
            node_id=node_id, node_type=node_type,
            properties=properties or {}, confidence=confidence,
        )
        self.nodes[node_id] = node

    def add_edge(self, source_id: str, target_id: str, relation: str,
                 weight: float = 1.0, properties: Dict = None):
        """Add an edge (relationship) between two nodes."""
        edge = Edge(
            source_id=source_id, target_id=target_id,
            relation=relation, weight=weight,
            properties=properties or {},
        )
        self.edges.append(edge)
        self._adjacency[source_id].append(edge)
        self._reverse_adjacency[target_id].append(edge)

    def get_node(self, node_id: str) -> Optional[Node]:
        """Get a node by ID."""
        node = self.nodes.get(node_id)
        if node:
            node.access_count += 1
        return node

    def get_neighbors(self, node_id: str,
                      relation: Optional[str] = None) -> List[Tuple[str, str]]:
        """Get neighbors of a node, optionally filtered by relation."""
        neighbors = []
        for edge in self._adjacency.get(node_id, []):
            if relation is None or edge.relation == relation:
                neighbors.append((edge.target_id, edge.relation))
        return neighbors

    def get_nodes_by_type(self, node_type: str) -> List[Node]:
        """Get all nodes of a given type."""
        return [n for n in self.nodes.values() if n.node_type == node_type]

    def get_edges_by_relation(self, relation: str) -> List[Edge]:
        """Get all edges with a given relation type."""
        return [e for e in self.edges if e.relation == relation]

    def find_path(self, start: str, end: str,
                  max_depth: int = 10) -> Optional[List[str]]:
        """Find a path between two nodes using BFS."""
        if start == end:
            return [start]

        visited = {start}
        queue = [(start, [start])]

        for _ in range(max_depth):
            next_queue = []
            for node_id, path in queue:
                for edge in self._adjacency.get(node_id, []):
                    if edge.target_id == end:
                        return path + [end]
                    if edge.target_id not in visited:
                        visited.add(edge.target_id)
                        next_queue.append((edge.target_id, path + [edge.target_id]))
            queue = next_queue
            if not queue:
                break

        return None

    def query(self, node_type: Optional[str] = None,
              relation: Optional[str] = None,
              min_confidence: float = 0.0,
              properties: Optional[Dict[str, Any]] = None) -> List[Node]:
        """Query nodes with filters."""
        results = []
        for node in self.nodes.values():
            if node_type and node.node_type != node_type:
                continue
            if node.confidence < min_confidence:
                continue
            if properties:
                match = True
                for k, v in properties.items():
                    if node.properties.get(k) != v:
                        match = False
                        break
                if not match:
                    continue
            results.append(node)
        return results

    def update_node(self, node_id: str, **kwargs):
        """Update node properties."""
        node = self.nodes.get(node_id)
        if node:
            for k, v in kwargs.items():
                if k == "confidence":
                    node.confidence = v
                else:
                    node.properties[k] = v
            node.last_updated = time.time()

    def remove_node(self, node_id: str):
        """Remove a node and all its edges."""
        self.nodes.pop(node_id, None)
        self.edges = [
            e for e in self.edges
            if e.source_id != node_id and e.target_id != node_id
        ]
        self._adjacency.pop(node_id, None)
        self._reverse_adjacency.pop(node_id, None)

    def get_subgraph(self, center_id: str, radius: int = 2) -> 'KnowledgeGraph':
        """Extract a subgraph around a center node."""
        subgraph = KnowledgeGraph()
        visited = {center_id}
        frontier = [center_id]

        for _ in range(radius):
            next_frontier = []
            for nid in frontier:
                if nid in self.nodes:
                    subgraph.nodes[nid] = self.nodes[nid]
                for edge in self._adjacency.get(nid, []):
                    if edge.target_id not in visited:
                        visited.add(edge.target_id)
                        next_frontier.append(edge.target_id)
                        subgraph.edges.append(edge)
                        if edge.target_id in self.nodes:
                            subgraph.nodes[edge.target_id] = self.nodes[edge.target_id]
            frontier = next_frontier

        return subgraph

    def get_stats(self) -> Dict[str, Any]:
        """Get graph statistics."""
        type_counts = defaultdict(int)
        for node in self.nodes.values():
            type_counts[node.node_type] += 1
        rel_counts = defaultdict(int)
        for edge in self.edges:
            rel_counts[edge.relation] += 1

        return {
            "total_nodes": len(self.nodes),
            "total_edges": len(self.edges),
            "node_types": dict(type_counts),
            "relation_types": dict(rel_counts),
        }


class WorldKnowledgeBuilder:
    """
    Builds and maintains the knowledge graph from simulation data.
    """

    def __init__(self, graph: KnowledgeGraph):
        self.graph = graph

    def register_building(self, building_id: str, x: float, y: float,
                           floors: int, building_type: str,
                           has_landing_pad: bool = False):
        self.graph.add_node(building_id, "building", {
            "x": x, "y": y, "floors": floors,
            "type": building_type,
            "has_landing_pad": has_landing_pad,
        })
        self.graph.add_edge(building_id, "world", "located_in")

    def register_charging_station(self, station_id: str, x: float, y: float):
        self.graph.add_node(station_id, "charging_station", {
            "x": x, "y": y,
        })

    def register_risk_zone(self, zone_id: str, x: float, y: float,
                            radius: float, risk_level: float):
        self.graph.add_node(zone_id, "risk_zone", {
            "x": x, "y": y, "radius": radius,
            "risk_level": risk_level,
        })

    def register_safe_corridor(self, corridor_id: str,
                                points: List[Tuple[float, float]],
                                success_rate: float):
        self.graph.add_node(corridor_id, "safe_corridor", {
            "points": points,
            "success_rate": success_rate,
        })

    def record_flight_experience(self, flight_id: str,
                                  start: Tuple, end: Tuple,
                                  path: List[Tuple],
                                  success: bool, battery_used: float):
        self.graph.add_node(flight_id, "flight_experience", {
            "start": start, "end": end,
            "path_length": len(path),
            "success": success,
            "battery_used": battery_used,
        })
        if success:
            self.graph.add_edge(flight_id, "world", "learned_from")