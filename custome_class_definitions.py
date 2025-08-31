from abc import ABC
from dataclasses import dataclass
from typing import List, Union 

#['festlager', 'loslager', 'einspannung', 'gelenk']



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
    from_node: str

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
class ProblemDefinition:
    name: str
    nodes: List[Node]
    connections: List[Connection]
    loads: List[Load]

    def __post_init__(self):
        self.node_map = {node.id: node for node in self.nodes}

    def node(self, id) -> Node:
        print(f"Retrieving node with id: {id}")
        return self.node_map.get(id)

Force = Union[Load, Bearing]