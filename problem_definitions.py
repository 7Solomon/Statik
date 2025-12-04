from models._analyze_custome_class import *

def einfeld_traeger():
    return ProblemDefinition(
        name="Einfeldträger",
        nodes=[
            Node(id="A", position=(0, 0), bearings=[
                Bearing(vector=(1, 0, 0), value=None),
                Bearing(vector=(0, 1, 0), value=None),
            ]),
            Node(id="B", position=(1, 0), bearings=[
                Bearing(vector=(0, 1, 0), value=None),
            ]),
        ],
        #loads=[
        #    Load(where="1", ve=(0.0, -10.0, 0.0)),
        #]
        loads=[
            PointLoad(position=(0.5, 0), ve=(0.0, -10.0, 0.0)),
        ]
    )

def einspannung():
    return ProblemDefinition(
        name="Einspannung",
        nodes=[
            Node(id="A", position=(0, 0), bearings=[
                Bearing(vector=(1, 0, 0), value=None),
                Bearing(vector=(0, 1, 0), value=None),
                Bearing(vector=(0, 0, 1), value=None),
            ]),
            Node(id="B", position=(1, 0), bearings=[]),
        ],
        loads=[
            PointLoad(position=(1, 0), ve=(0.0, -10.0, 0.0)),
        ]
    )

def complex_problem():
    return ProblemDefinition(
        name="complex",
        nodes=[
            Node(id="1", position=(0, 0), reactions=[
                Bearing(vector=(1, 0, 0), value=None),
                Bearing(vector=(0, 1, 0), value=None),
                Joint(vector=(1, 0, 0), to_node="2"),
                Joint(vector=(0, 1, 0), to_node="2"),
            ]),
            Node(id="2", position=(1, 0), reactions=[
                Joint(vector=(1, 0, 0), to_node="1"),
                Joint(vector=(0, 0, 1), to_node="1"),
                Joint(vector=(1, 0, 0), to_node="3"),
                Joint(vector=(0, 0, 1), to_node="3"),
            ]),
            Node(id="3", position=(2, 0), reactions=[
                Joint(vector=(1, 0, 0), to_node="2"),
                Joint(vector=(0, 1, 0), to_node="2"),
                Joint(vector=(0, 0, 1), to_node="2"),
                Joint(vector=(1, 0, 0), to_node="4"),
                Joint(vector=(0, 1, 0), to_node="4"),
                Joint(vector=(0, 0, 1), to_node="4"),
                Joint(vector=(1, 0, 0), to_node="9"),
                Joint(vector=(0, 1, 0), to_node="9"),
                Joint(vector=(0, 0, 1), to_node="9"),
            ]),
            Node(id="4", position=(3, 0), reactions=[
                Joint(vector=(1, 0, 0), to_node="3"),
                Joint(vector=(0, 1, 0), to_node="3"),
                Joint(vector=(0, 0, 1), to_node="3"),
                Joint(vector=(1, 0, 0), to_node="5"),
                Joint(vector=(0, 1, 0), to_node="5"),
                Joint(vector=(0, 0, 1), to_node="5"),
                Joint(vector=(1, 0, 0), to_node="7"),
                Joint(vector=(0, 1, 0), to_node="7"),
            ]),
            Node(id="5", position=(4, 0), reactions=[
                Joint(vector=(1, 0, 0), to_node="4"),
                Joint(vector=(0, 1, 0), to_node="4"),
                Joint(vector=(0, 0, 1), to_node="4"),
                Joint(vector=(1, 0, 0), to_node="6"),
                Joint(vector=(0, 1, 0), to_node="6"),
                Joint(vector=(0, 0, 1), to_node="6"),
                Joint(vector=(1, 0, 0), to_node="8"),
                Joint(vector=(0, 1, 0), to_node="8"),
                Joint(vector=(0, 0, 1), to_node="8"),
                Joint(vector=(1, 0, 0), to_node="10"),
                Joint(vector=(0, 1, 0), to_node="10"),
                Joint(vector=(0, 0, 1), to_node="10"),
            ]),
            Node(id="6", position=(5, 0), reactions=[
                Joint(vector=(1, 0, 0), to_node="5"),
                Joint(vector=(0, 1, 0), to_node="5"),
                Joint(vector=(0, 0, 1), to_node="5"),  # Moment muss null sein aber nur durch logik
            ]),
            Node(id="7", position=(3, 1), reactions=[
                Bearing(vector=(1, 0, 0), value=None),
                Bearing(vector=(0, 1, 0), value=None),
                Joint(vector=(1, 0, 0), to_node="4"),
                Joint(vector=(0, 1, 0), to_node="4"),
            ]),
            Node(id="8", position=(4, 1), reactions=[
                Joint(vector=(1, 0, 0), to_node="5"),
                Joint(vector=(0, 1, 0), to_node="5"),
                Joint(vector=(0, 0, 1), to_node="5"),  # Same moment type shit
            ]),
            Node(id="9", position=(2, -1), reactions=[
                Bearing(vector=(0, 1, 0), value=None),
                Joint(vector=(1, 0, 0), to_node="3"),
                Joint(vector=(0, 1, 0), to_node="3"),

            ]),
            Node(id="10", position=(4, -1), reactions=[
                Joint(vector=(1, 0, 0), to_node="5"),
                Joint(vector=(0, 1, 0), to_node="5"),
                Joint(vector=(0, 0, 1), to_node="5"),  # Same moment type shit
            ]),
        ],
        loads=[
            PointLoad(position=(7, 1), ve=(25.0, 0.0, 0.0)),
            PointLoad(position=(7, -1), ve=(25.0, 0.0, 0.0)),
            DistributedLoad(position=((0, 0), (5, 0)), ve=(0.0, -5.0, 0.0)),
        ]
    )
def complex_problem_v2():
    return ProblemDefinition(
    name="complex2",
    nodes=[
        Node(id="1", position=(0, 0), reactions=[
            Bearing(vector=(1, 0, 0), value=None),
            Bearing(vector=(0, 0, 1), value=None),
            Joint(vector=(1, 0, 0), to_node="2"),
            Joint(vector=(0, 0, 1), to_node="2"),
        ]),
        Node(id="2", position=(2, 0), reactions=[
            Joint(vector=(1, 0, 0), to_node="1"),
            Joint(vector=(0, 1, 0), to_node="1"),
            Joint(vector=(0, 0, 1), to_node="1"),
            Joint(vector=(1, 0, 0), to_node="3"),
            Joint(vector=(0, 1, 0), to_node="3"),
            Joint(vector=(0, 0, 1), to_node="3"),
            Joint(vector=(1, 0, 0), to_node="7"),
            Joint(vector=(0, 1, 0), to_node="7"),
            Joint(vector=(0, 0, 1), to_node="7"),
        ]),
        Node(id="3", position=(4, 0), reactions=[
            Joint(vector=(0, 1, 0), to_node="2"),
            Joint(vector=(0, 0, 1), to_node="2"),
            Joint(vector=(0, 1, 0), to_node="4"),
            Joint(vector=(0, 0, 1), to_node="4"),
        ]),
        Node(id="4", position=(6, 0), reactions=[
            Joint(vector=(1, 0, 0), to_node="3"),
            Joint(vector=(0, 1, 0), to_node="3"),
            Joint(vector=(0, 0, 1), to_node="3"),
            Joint(vector=(1, 0, 0), to_node="5"),
            Joint(vector=(0, 1, 0), to_node="5"),
            Joint(vector=(0, 0, 1), to_node="5"),
            Joint(vector=(1, 0, 0), to_node="6"),
            Joint(vector=(0, 1, 0), to_node="6"),
            Joint(vector=(0, 0, 1), to_node="6"),

        ]),
        Node(id="5", position=(8, 0), reactions=[
            Joint(vector=(1, 0, 0), to_node="4"),
            Joint(vector=(0, 1, 0), to_node="4"),
            Joint(vector=(1, 0, 0), to_node="9"),
            Joint(vector=(0, 1, 0), to_node="9"),
            Joint(vector=(1, 0, 0), to_node="10"),
            Joint(vector=(0, 1, 0), to_node="10"),
            Joint(vector=(1, 0, 0), to_node="12"),
            Joint(vector=(0, 1, 0), to_node="12"),
            Joint(vector=(1, 0, 0), to_node="13"),
            Joint(vector=(0, 1, 0), to_node="13"),
        ]),
        Node(id="6", position=(4, 1), reactions=[
            Joint(vector=(1, 0, 0), to_node="4"),
            Joint(vector=(0, 1, 0), to_node="4"),
            Joint(vector=(0, 0, 1), to_node="4"),
        ]),
        Node(id="7", position=(2, -1), reactions=[
            Joint(vector=(1, 0, 0), to_node="2"),
            Joint(vector=(0, 1, 0), to_node="2"),
            Joint(vector=(0, 0, 1), to_node="2"),
            Joint(vector=(1, 0, 0), to_node="8"),
            Joint(vector=(0, 1, 0), to_node="8"),
            Joint(vector=(0, 0, 1), to_node="8"),
        ]),
        Node(id="8", position=(4, -1), reactions=[
            Joint(vector=(1, 0, 0), to_node="7"),
            Joint(vector=(0, 1, 0), to_node="7"),
            Joint(vector=(0, 0, 1), to_node="7"),
        ]),
        Node(id="9", position=(10, 0), reactions=[
            Bearing(vector=(-1, 0, 0), value=None),
            Joint(vector=(1, 0, 0), to_node="5"),
            Joint(vector=(0, 1, 0), to_node="5"),
            Joint(vector=(1, 0, 0), to_node="12"),
            Joint(vector=(0, 1, 0), to_node="12"),
            Joint(vector=(1, 0, 0), to_node="13"),
            Joint(vector=(0, 1, 0), to_node="13"),
        ]),
        Node(id="10", position=(8, 1), reactions=[
            Joint(vector=(1, 0, 0), to_node="5"),
            Joint(vector=(0, 1, 0), to_node="5"),
            Joint(vector=(1, 0, 0), to_node="11"),
            Joint(vector=(0, 1, 0), to_node="11"),
            Joint(vector=(1, 0, 0), to_node="12"),
            Joint(vector=(0, 1, 0), to_node="12"),
        ]),
        Node(id="11", position=(10, 2), reactions=[
            Joint(vector=(1, 0, 0), to_node="10"),
            Joint(vector=(0, 1, 0), to_node="10"),
            Joint(vector=(1, 0, 0), to_node="12"),
            Joint(vector=(0, 1, 0), to_node="12"),
        ]),
        Node(id="12", position=(10, 1), reactions=[
            Joint(vector=(1, 0, 0), to_node="10"),
            Joint(vector=(0, 1, 0), to_node="10"),
            Joint(vector=(1, 0, 0), to_node="11"),
            Joint(vector=(0, 1, 0), to_node="11"),
            Joint(vector=(1, 0, 0), to_node="9"),
            Joint(vector=(0, 1, 0), to_node="9"),
            Joint(vector=(1, 0, 0), to_node="5"),
            Joint(vector=(0, 1, 0), to_node="5"),
        ]),
        Node(id="13", position=(10, -2), reactions=[
            Bearing(vector=(1, 0, 0), value=None),
            Bearing(vector=(0, 1, 0), value=None),
            Joint(vector=(1, 0, 0), to_node="5"),
            Joint(vector=(0, 1, 0), to_node="5"),
            Joint(vector=(1, 0, 0), to_node="9"),
            Joint(vector=(0, 1, 0), to_node="9"),
        ]),
    ],
    loads=[
        PointLoad(position=(4, -2), ve=(0.0, -25.0, 0.0)),
        PointLoad(position=(4, -2), ve=(25.0, 0.0, 0.0)),
        PointLoad(position=(6, 2), ve=(25.0, 0.0, 0.0)),
        DistributedLoad(position=((0, 0), (8, 0)), ve=(0.0, -5.0, 0.0)),
    ]
)
