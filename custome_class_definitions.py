from abc import ABC
from dataclasses import dataclass
from typing import List, Union 

#['festlager', 'loslager', 'einspannung', 'gelenk']



@dataclass
class Connection:
    id: str
    from_node: str
    to_node: str
    length: float

    #EA: float
    #EI: float

@dataclass
class Bearing:
    position: tuple[float, float]
    vector: tuple[float, float, float]

    value: float | None


@dataclass
class Node:
    id: str
    position: tuple[float, float]
    bearings: List[Bearing]


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


Force = Union[Load, Bearing]