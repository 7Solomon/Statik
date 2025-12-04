from abc import ABC
from dataclasses import dataclass
from typing import List, Set, Union

#['festlager', 'loslager', 'einspannung', 'gelenk']

@dataclass
class Vec:
    x: float
    y: float
    m: float

    def __init__(self, x: float, y: float, m: float):
        self.x = x
        self.y = y
        self.m = m

    @property
    def vec(self):
        return (self.x, self.y, self.m)
    


@dataclass
class Connection:
    #id: str
    from_node: str
    to_node: str
    length: float = None

    #EA: float
    #EI: float

@dataclass
class Bearing:
    vector: tuple[float, float, float]
    value: float | None

@dataclass
class Joint:
    vector: tuple[float, float, float]
    to_node: str
    #value: float | None


@dataclass
class Node:
    id: str
    position: tuple[float, float]
    reactions: List[Bearing | Joint]



@dataclass
class Festlager:
    type: str = 'festlager'

@dataclass
class Load(ABC):
    ve: tuple[float, float, float]
@dataclass
class PointLoad(Load):
    position: tuple[float, float]
@dataclass
class DistributedLoad(Load):
    position: tuple[tuple[float, float], tuple[float, float]]


@dataclass
class SubSystem:
    id: str
    nodes: Set[Node]
    bearings: List[Bearing]
    joints: List[Joint]

    isNotKinematic: bool | None = None



@dataclass
class ProblemDefinition:
    name: str
    nodes: List[Node]
    #connections: List[Connection]
    loads: List[Load]

    def __post_init__(self):
        self.node_map = {node.id: node for node in self.nodes}

    @property
    def connections(self) -> List[Connection]:
        edges: dict[tuple[str,str], Connection] = {}
        for node in self.nodes:
            for reac in getattr(node, "reactions", []):
                if isinstance(reac, Joint):
                    a, b = node.id, reac.to_node
                    if a == b:
                        continue
                    key = tuple(sorted((a, b)))
                    if key not in edges:
                        n1 = self.node_map.get(key[0])
                        n2 = self.node_map.get(key[1])
                        length = None
                        if n1 and n2:
                            dx = n2.position[0] - n1.position[0]
                            dy = n2.position[1] - n1.position[1]
                            length = (dx*dx + dy*dy) ** 0.5
                        # Store normalized direction (from_node < to_node) once
                        edges[key] = Connection(from_node=key[0], to_node=key[1], length=length)
        return list(edges.values())

    def node(self, id) -> Node:
        #print(f"Retrieving node with id: {id}")
        return self.node_map.get(id)

Force = Union[Load, Bearing]
