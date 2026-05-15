r"""
How to use:
    python Solver.py instance_name.txt
    python Solver.py instance_name.txt -- validate

The first command line argument creates the solution file
The second command line argument also creates the solution file but also checks if the solution is valid
"""

import os
import argparse
import sys

from InstanceCVRPTWUI import InstanceCVRPTWUI
from Validate import SolutionCVRPTWUI

from greedyBaseline import *
from routingSequential import *
from routingParallel import build_routes_parallel_regret, build_routes_parallel_regret_two_step
from schedulingScored import assign_delivery_days_scored
from localSearch import strip_depots, add_depots, local_search

def resolve_instance_path(path):
    if os.path.exists(path):
        return path
    fallback = os.path.join("instances 2026", "instances", os.path.basename(path))
    if os.path.exists(fallback):
        return fallback
    print(f"ERROR: instance file not found: {path}")
    sys.exit(1)

def solve(instance_path, output_path):
    inst = InstanceCVRPTWUI(instance_path)
    if not inst.isValid():
        print(f"ERROR: invalid instance {instance_path}")
        for error in inst.errorReport:
            print(f"  {error}")
        sys.exit(1)

    inst.calculateDistances()
    dist = calculate_all_distances(inst)
    
    print(f"{os.path.basename(instance_path)}")
    print(f"Days={inst.Days}  Requests={len(inst.Requests)}  Customers={len(inst.Coordinates)-1}  Tools={len(inst.Tools)}")

    print(f"assign delivery days:")
    delivery_day = assign_delivery_days_scored(inst, dist)

    print(f"build routes:")

    candidates = []

    routes = maker_of_routes(inst, delivery_day)
    _, _, _, _, cost = compute_cost(inst, dist, routes)
    candidates.append(("baseline", routes, cost))
    print(f"baseline cost: {cost:,}")

    routes = build_routes_sequential_ex(inst, delivery_day, dist)
    _, _, _, _, cost = compute_cost(inst, dist, routes)
    candidates.append(("sequential extra-mileage", routes, cost))
    
    print(f"sequential extra-mileage cost: {cost:,}")

    routes = build_routes_parallel_regret(inst, delivery_day, dist)
    _, _, _, _, cost = compute_cost(inst, dist, routes)
    candidates.append(("parallel regret", routes, cost))
    print(f"parallel regret cost: {cost:,}")


    routes = build_routes_parallel_regret_two_step(inst, delivery_day, dist)
    _, _, _, _, cost = compute_cost(inst, dist, routes)
    candidates.append(("two-step parallel regret", routes, cost))
    print(f"two-step parallel regret cost: {cost:,}")

    best_name, days_routes, best_cost = min(candidates, key=lambda x: x[2])

    print(f"selected routing heuristic: {best_name}")
    print(f"selected cost before local search: {best_cost:,}")

    print(f"run local search")
    routes_before_ls = days_routes
    cost_before_ls = best_cost

    bare = strip_depots(days_routes)
    improved = local_search(bare, inst, dist, max_seconds=5.0, max_iterations=5000)
    routes_after_ls = add_depots(improved)

    _, _, _, _, cost_after_ls = compute_cost(inst, dist, routes_after_ls)

    if cost_after_ls < cost_before_ls:
        days_routes = routes_after_ls
        print(f"Local search improved: {cost_before_ls:,} -> {cost_after_ls:,}")
    else:
        days_routes = routes_before_ls
        print(f"Local search worsened: {cost_before_ls:,} -> {cost_after_ls:,}")

    cost = fun_sol_output_writer(inst, dist, delivery_day, days_routes, output_path)

    return cost

def run_validator(instance_path, solution_path):
    """Run the validator so we know if our solution is valid"""
    print(f"Validating solution...")

    instance = InstanceCVRPTWUI(instance_path)
    solution = SolutionCVRPTWUI(solution_path, instance)

    if solution.isValid():
        print(f"Solution {solution_path} is a valid CVRPTWUI solution")

        correct_info, message = solution.areGivenValuesValid()

        if correct_info:
            print(f"The given solution information is correct")
        else:
            print(message)

        print(str(solution.calcCost).split("\n"))

        return True

    else:
        print(f"File {solution_path} is an invalid CVRPTWUI solution file")
        print(solution.errorReport)

        return False

def main():
    parser = argparse.ArgumentParser(prog="Solver.py", description=("VeRoLog 2017\n\n")
    )
    parser.add_argument('input', nargs='?')
    parser.add_argument('-i', metavar='FILE')
    parser.add_argument('-o', metavar='FILE')
    parser.add_argument('--validate', action='store_true')
    
    args = parser.parse_args()

    instance_path = args.i or args.input
    if instance_path:
        instance_path = resolve_instance_path(instance_path)

    if not instance_path:
        parser.print_help()
        return
    
    output = args.o or instance_path.replace('.txt', '_solution.txt')
    solve(instance_path, output)
    if args.validate:
        run_validator(instance_path, output)
    
if __name__ == '__main__':
    main()