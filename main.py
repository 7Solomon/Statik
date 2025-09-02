
from functions import check_static_determinacy, split_in_base_systems
from problem_definitions import *



def test_verlauf_checker():
    #definition = einfeld_traeger()
    #definition = einspannung()
    #definition = complex_problem()
    definition = complex_problem_v2()


    f = check_static_determinacy(definition)
    print(f"Degree of static indeterminacy: {f}")
    if f == 0:
        split_in_base_systems(definition)
    else:
        print("The system is not statically determinate, cannot calculate reaction forces.")


if __name__ == "__main__":
    test_verlauf_checker()