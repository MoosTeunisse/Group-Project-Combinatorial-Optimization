"""
How to use:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
"""

import os
import sys
import argparse
import subprocess
import random

from InstanceCVRPTWUI import InstanceCVRPTWUI

from greedyBaseline import (
    build_dist_matrix,
    assign_delivery_days,
    build_routes_baseline,
    compute_cost,
    write_solution
)

from routingSequential import *

from routingParallel import (
    build_routes_parallel_regret,
    build_routes_parallel_regret_two_step
)

from schedulingScored import (
    assign_delivery_days_scored
)

from localSearch import (
    strip_depots,
    add_depots,
    local_search
)

# Solver

def solve(instance_path, output_path, verbose=True):
    """Run Step 2 and Step 3 for a single instance."""
    inst = InstanceCVRPTWUI(instance_path)
    if not inst.isValid():
        print(f"ERROR: invalid instance {instance_path}")
        for error in inst.errorReport:
            print(f"  {error}")
        sys.exit(1)

    inst.calculateDistances()
    dist = build_dist_matrix(inst)
    
    if verbose:
        print(f"\n{'='*55}")
        print(f"  {os.path.basename(instance_path)}")
        print(f"{'='*55}")
        print(f"  Days={inst.Days}  Requests={len(inst.Requests)}"
              f"  Customers={len(inst.Coordinates)-1}  Tools={len(inst.Tools)}")

    if verbose:
        print("\n  assign delivery days")
    # delivery_day = assign_delivery_days(inst)
    delivery_day = assign_delivery_days_scored(inst, dist)

    if verbose:
        print("  build routes")

    candidates = []

    # Candidate 1: baseline
    try:
        routes = build_routes_baseline(inst, delivery_day)
        _, _, _, _, cost = compute_cost(inst, dist, delivery_day, routes)
        candidates.append(("baseline", routes, cost))
        if verbose:
            print(f"    baseline cost: {cost:,}")
    except Exception as e:
        if verbose:
            print(f"    baseline failed: {e}")

    # Candidate 2: sequential extra-mileage
    try:
        routes = build_routes_sequential_ex(inst, delivery_day, dist)
        _, _, _, _, cost = compute_cost(inst, dist, delivery_day, routes)
        candidates.append(("sequential extra-mileage", routes, cost))
        if verbose:
            print(f"    sequential extra-mileage cost: {cost:,}")
    except Exception as e:
        if verbose:
            print(f"    sequential extra-mileage failed: {e}")

    # Candidate 3: parallel regret
    try:
        routes = build_routes_parallel_regret(inst, delivery_day, dist)
        _, _, _, _, cost = compute_cost(inst, dist, delivery_day, routes)
        candidates.append(("parallel regret", routes, cost))
        if verbose:
            print(f"    parallel regret cost: {cost:,}")
    except Exception as e:
        if verbose:
            print(f"    parallel regret failed: {e}")

    # Candidate 4: two-step parallel regret
    try:
        routes = build_routes_parallel_regret_two_step(inst, delivery_day, dist)
        _, _, _, _, cost = compute_cost(inst, dist, delivery_day, routes)
        candidates.append(("two-step parallel regret", routes, cost))
        if verbose:
            print(f"    two-step parallel regret cost: {cost:,}")
    except Exception as e:
        if verbose:
            print(f"    two-step parallel regret failed: {e}")

    if len(candidates) == 0:
        print("ERROR: no routing heuristic produced a solution")
        sys.exit(1)

    best_name, days_routes, best_cost = min(candidates, key=lambda x: x[2])

    if verbose:
        print(f"  selected routing heuristic: {best_name}")
        print(f"  selected cost before local search: {best_cost:,}")

    if verbose:
        print("  run local search")

    routes_before_ls = days_routes
    cost_before_ls = best_cost

    bare = strip_depots(days_routes)
    improved = local_search(
        bare,
        inst,
        dist,
        max_seconds=5.0,
        max_iterations=5000
    )
    routes_after_ls = add_depots(improved)

    _, _, _, _, cost_after_ls = compute_cost(
        inst,
        dist,
        delivery_day,
        routes_after_ls
    )

    if cost_after_ls < cost_before_ls:
        days_routes = routes_after_ls
        if verbose:
            print(f"  local search accepted: {cost_before_ls:,} -> {cost_after_ls:,}")
    else:
        days_routes = routes_before_ls
        if verbose:
            print(f"  local search rejected: {cost_before_ls:,} -> {cost_after_ls:,}")

    if verbose:
        print("  write solution")
    cost = write_solution(inst, dist, delivery_day, days_routes, output_path)

    if verbose:
        max_v, vdays, tool_use, distance, _ = compute_cost(
            inst, dist, delivery_day, days_routes)
        print(f"\n  ── Cost breakdown (Step 3) ────────────────────────")
        print(f"  VEHICLE_COST     x {max_v:>5} = {max_v * inst.VehicleCost:>18,}")
        print(f"  VEHICLE_DAY_COST x {vdays:>5} = {vdays * inst.VehicleDayCost:>18,}")
        print(f"  DISTANCE_COST    x {distance:>5} = {distance * inst.DistanceCost:>18,}")
        for i, t in enumerate(inst.Tools):
            print(f"  Tool {t.ID} cost      x {tool_use[i]:>5} = {tool_use[i] * t.cost:>18,}")
        print(f"  {'─'*48}")
        print(f"  TOTAL COST               = {cost:>18,}")
        print(f"  File                     : {output_path}")

    return cost


# Validator

def run_validator(instance_path, solution_path, validator_dir=None):
    """Call the official Validate.py."""
    if validator_dir is None:
        validator_dir = os.path.dirname(os.path.abspath(__file__))
    validate_py = os.path.join(validator_dir, 'Validate.py')
    if not os.path.isfile(validate_py):
        print(f"[!] Validate.py not found in: {validator_dir}")
        return
    print("\n[Validator] Checking solution...")
    r = subprocess.run(
        [sys.executable, validate_py, '-i', instance_path, '-s', solution_path],
        capture_output=True, text=True
    )
    print(r.stdout)
    if r.stderr:
        print("STDERR:", r.stderr)

def main():
    parser = argparse.ArgumentParser(
        prog="Solver.py",
        description=(
            "VeRoLog 2017 — Step 2 (Greedy Baseline) + Step 3 (Cost)\n\n"
            "Examples:\n"
            "  python Solver.py -i instances/testInstance.txt -o solutions/sol.txt\n"
            "  python Solver.py -i instances/testInstance.txt"
            " -o solutions/sol.txt --validate\n"
            "  python Solver.py --batch instances/ solutions/\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument('-i', '--instance',    metavar='FILE')
    parser.add_argument('-o', '--output',      metavar='FILE')
    parser.add_argument('--batch', nargs=2,    metavar=('INST_DIR', 'SOL_DIR'))
    parser.add_argument('--validate',          action='store_true')
    parser.add_argument('--validator-dir',     metavar='DIR', dest='validator_dir')
    parser.add_argument('--seed', type=int,    default=42)
    parser.add_argument('--quiet',             action='store_true')

    args    = parser.parse_args()
    random.seed(args.seed)
    verbose = not args.quiet

    if args.instance:
        output = args.output or args.instance.replace('.txt', '_solution.txt')
        solve(args.instance, output, verbose=verbose)
        if args.validate:
            run_validator(args.instance, output, args.validator_dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()