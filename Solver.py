"""
=============================================================================
VeRoLog 2017 
=============================================================================

FILE STRUCTURE (place all files in the same directory):
    Solver.py              <-- THIS FILE
    baseCVRPTWUI.py         <-- from the zip, DO NOT modify
    InstanceCVRPTWUI.py     <-- from the zip, DO NOT modify
    Validate.py             <-- from the zip, DO NOT modify

USAGE:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
    python Solver.py --batch instances/ solutions/

WHAT DOES THIS FILE DO?
    This is the main solver file.
    It reads an instance, computes a solution using a method, writes
    the solution to a file, and optionally validates it.
=============================================================================
"""

import math
import os
import sys
import argparse
import subprocess
import random
import copy
from collections import defaultdict

from InstanceCVRPTWUI import InstanceCVRPTWUI

from greedyBaseline import (
    build_dist_matrix,
    assign_delivery_days,
    build_routes_baseline,
    compute_cost,
    write_solution
)

from routingSequential import (
    build_day_tasks,
    route_distance,
    required_initial_load,
    route_load_feasible,
    is_route_feasible,
    best_insertion_in_route,
    pivot_score,
    choose_pivot,
    build_routes_sequential_ex_day,
    build_routes_sequential_ex
)

from routingParallel import (
    build_routes_parallel_regret
)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

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
        print("\n  [Step 2A] Assigning delivery days (+ repair)...")
    delivery_day = assign_delivery_days(inst)

    if verbose:
        print("  [Step 5] Building routes (Parallel)...")
    # days_routes = build_routes_baseline(inst, delivery_day)
    # days_routes = build_routes_sequential_ex(inst, delivery_day, dist)
    days_routes = build_routes_parallel_regret(inst, delivery_day, dist)

    if verbose:
        print("  [Step 2C] Writing solution...")
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


# =============================================================================
# BATCH
# =============================================================================

def solve_batch(instances_dir, solutions_dir, verbose=True):
    """Solve all .txt instances in a directory."""
    os.makedirs(solutions_dir, exist_ok=True)
    files = sorted(f for f in os.listdir(instances_dir) if f.endswith('.txt'))
    if not files:
        print(f"No .txt files found in: {instances_dir}")
        return
    results = []
    total   = 0
    for filename in files:
        cost = solve(
            os.path.join(instances_dir, filename),
            os.path.join(solutions_dir, filename.replace('.txt', '_solution.txt')),
            verbose=verbose
        )
        results.append((filename, cost))
        total += cost
    print(f"\n{'='*60}\nOVERVIEW\n{'='*60}")
    for filename, cost in results:
        print(f"  {filename:<45}  {cost:>15,}")
    print(f"{'─'*60}\n  Total: {total:>51,}\n{'='*60}")


# =============================================================================
# VALIDATOR
# =============================================================================

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


# =============================================================================
# CLI
# =============================================================================

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

    if args.batch:
        solve_batch(args.batch[0], args.batch[1], verbose=verbose)
    elif args.instance:
        output = args.output or args.instance.replace('.txt', '_solution.txt')
        solve(args.instance, output, verbose=verbose)
        if args.validate:
            run_validator(args.instance, output, args.validator_dir)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()