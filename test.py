
from custome_class_definitions import *
from functions import calculate_reaction_forces, check_static_determinacy, split_in_base_systems

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
        connections=[
            Connection(id="1", from_node="A", to_node="B", length=1.0),
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
        connections=[
            Connection(id="1", from_node="A", to_node="B", length=1.0),
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
                Joint(vector=(1, 0, 0), from_node="2"),
                Joint(vector=(0, 1, 0), from_node="2"),
            ]),
            Node(id="2", position=(1, 0), reactions=[
                Joint(vector=(0, 1, 0), from_node="1"),
                Joint(vector=(0, 0, 1), from_node="1"),
                Joint(vector=(0, 1, 0), from_node="3"),
                Joint(vector=(0, 0, 1), from_node="3"),
            ]),
            Node(id="3", position=(2, 0), reactions=[
                Joint(vector=(1, 0, 0), from_node="2"),
                Joint(vector=(0, 1, 0), from_node="2"),
                Joint(vector=(0, 0, 1), from_node="2"),
                Joint(vector=(1, 0, 0), from_node="4"),
                Joint(vector=(0, 1, 0), from_node="4"),
                Joint(vector=(0, 0, 1), from_node="4"),
                Joint(vector=(1, 0, 0), from_node="9"),
                Joint(vector=(0, 1, 0), from_node="9"),
                Joint(vector=(0, 0, 1), from_node="9"),
            ]),
            Node(id="4", position=(3, 0), reactions=[
                Joint(vector=(1, 0, 0), from_node="3"),
                Joint(vector=(0, 1, 0), from_node="3"),
                Joint(vector=(0, 0, 1), from_node="3"),
                Joint(vector=(1, 0, 0), from_node="5"),
                Joint(vector=(0, 1, 0), from_node="5"),
                Joint(vector=(0, 0, 1), from_node="5"),
                Joint(vector=(1, 0, 0), from_node="7"),
                Joint(vector=(0, 1, 0), from_node="7"),
            ]),
            Node(id="5", position=(4, 0), reactions=[
                Joint(vector=(1, 0, 0), from_node="4"),
                Joint(vector=(0, 1, 0), from_node="4"),
                Joint(vector=(0, 0, 1), from_node="4"),
                Joint(vector=(1, 0, 0), from_node="6"),
                Joint(vector=(0, 1, 0), from_node="6"),
                Joint(vector=(0, 0, 1), from_node="6"),
                Joint(vector=(1, 0, 0), from_node="8"),
                Joint(vector=(0, 1, 0), from_node="8"),
                Joint(vector=(0, 0, 1), from_node="8"),
                Joint(vector=(1, 0, 0), from_node="10"),
                Joint(vector=(0, 1, 0), from_node="10"),
                Joint(vector=(0, 0, 1), from_node="10"),
            ]),
            Node(id="6", position=(5, 0), reactions=[
                Joint(vector=(1, 0, 0), from_node="5"),
                Joint(vector=(0, 1, 0), from_node="5"),
                Joint(vector=(0, 0, 1), from_node="5"),  # Moment muss null sein aber nur durch logik
            ]),
            Node(id="7", position=(3, 1), reactions=[
                Bearing(vector=(1, 0, 0), value=None),
                Bearing(vector=(0, 1, 0), value=None),
                Joint(vector=(1, 0, 0), from_node="4"),
                Joint(vector=(0, 1, 0), from_node="4"),
            ]),
            Node(id="8", position=(4, 1), reactions=[
                Joint(vector=(1, 0, 0), from_node="5"),
                Joint(vector=(0, 1, 0), from_node="5"),
                Joint(vector=(0, 0, 1), from_node="5"),  # Same moment type shit
            ]),
            Node(id="9", position=(2, -1), reactions=[
                Bearing(vector=(1, 0, 0), value=None),
                Joint(vector=(1, 0, 0), from_node="3"),
                Joint(vector=(0, 1, 0), from_node="3"),
            ]),
            Node(id="10", position=(4, -1), reactions=[
                Joint(vector=(1, 0, 0), from_node="5"),
                Joint(vector=(0, 1, 0), from_node="5"),
                Joint(vector=(0, 0, 1), from_node="5"),  # Same moment type shit
            ]),
        ],
        connections=[
            Connection(from_node="1", to_node="2"),
            Connection(from_node="2", to_node="3"),
            Connection(from_node="3", to_node="4"),
            Connection(from_node="4", to_node="5"),
            Connection(from_node="5", to_node="6"),
            Connection(from_node="4", to_node="7"),
            Connection(from_node="5", to_node="8"),
            Connection(from_node="3", to_node="9"),
            Connection(from_node="5", to_node="10"),
        ],
        loads=[
            PointLoad(position=(7, 1), ve=(25.0, 0.0, 0.0)),
            PointLoad(position=(7, -1), ve=(25.0, 0.0, 0.0)),
            DistributedLoad(position=((0, 0), (5, 0)), ve=(0.0, -5.0, 0.0)),
        ]
    )

def test_verlauf_checker():
    #definition = einfeld_traeger()
    #definition = einspannung()
    definition = complex_problem()
    f = check_static_determinacy(definition)
    print(f"Degree of static indeterminacy: {f}")
    if f == 0:
        #calculate_reaction_forces(definition)
        split_in_base_systems(definition)
    else:
        print("The system is not statically determinate, cannot calculate reaction forces.")


if __name__ == "__main__":
    test_verlauf_checker()