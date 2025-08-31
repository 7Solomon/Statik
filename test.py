
from custome_class_definitions import *
from functions import calculate_reaction_forces, check_static_determinacy

def einfeld_traeger():
    return ProblemDefinition(
        name="Einfeldträger",
        nodes=[
            Node(id="A", position=(0, 0), bearings=[
                Bearing(position=(0, 0), vector=(1, 0, 0)),
                Bearing(position=(0, 0), vector=(0, 1, 0)),
            ]),
            Node(id="B", position=(1, 0), bearings=[
                Bearing(position=(1, 0), vector=(0, 1, 0)),
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
                Bearing(position=(0, 0), vector=(1, 0, 0)),
                Bearing(position=(0, 0), vector=(0, 1, 0)),
                Bearing(position=(0, 0), vector=(0, 0, 1)),
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

def test_verlauf_checker():
    #definition = einfeld_traeger()
    definition = einspannung()
    f = check_static_determinacy(definition)
    print(f"Degree of static indeterminacy: {f}")
    if f == 0:
        calculate_reaction_forces(definition)
    else:
        print("The system is not statically determinate, cannot calculate reaction forces.")


if __name__ == "__main__":
    test_verlauf_checker()