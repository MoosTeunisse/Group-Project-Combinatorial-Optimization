import math
import os
import sys
import argparse
import subprocess
import random
import copy
from collections import defaultdict

from InstanceCVRPTWUI import InstanceCVRPTWUI


def calculate_all_distances(instance_data):

    # n    = len(instance_data.Coordinates)
    
    all_locations=instance_data.Coordinates
    amount_of_locations=len(all_locations)
    row_with_zero=[0] * amount_of_locations
    distance_table = [row_with_zero[:] for _ in range(amount_of_locations)]
    for i in range(amount_of_locations):
       # ci = instance_data.Coordinates[i]
        for j in range(i + 1, amount_of_locations):
            firstX, firstY=all_locations[i].X, all_locations[i].Y
            secondX, secondY=all_locations[j].X, all_locations[j].Y
          #  cj = instance_data.Coordinates[j]
            difference_X=firstX- secondX
            difference_Y= firstY- secondY

            distance  = int(math.floor(math.sqrt((difference_X) ** 2 + 
                                            (difference_Y) ** 2)))
            distance_table[i][j] = distance
            distance_table[j][i] = distance
    return distance_table

# 1. Check of een dag haalbaar is (klein, duidelijk)
def possible_on_day(request, given_day, occupied_tools, maximum_amount_of_tools_of_type):
    last_day=given_day + request.numDays + 1
    for day in range(given_day, last_day):
        total_amount_of_tools_of_type=occupied_tools.get((day, request.tool),0) + request.toolCount
        if total_amount_of_tools_of_type > maximum_amount_of_tools_of_type:
            return False
    return True
# 2. Vind de beste dag voor een request (bevat de noodoplossing)
def obtain_optimal_day(request, occupied_tools, maximum_amount_of_tools_of_type):
    """Find earliest feasible day, or day with lowest peak."""
    starting_day=request.fromDay
    ending_day=request.toDay + 1
    for day in range(starting_day, ending_day):
        if possible_on_day(request, day, occupied_tools, maximum_amount_of_tools_of_type):
            return day
    else:
    # Emergency fallback
     all_deleverable_days=range(request.fromDay, request.toDay + 1)
     def score(pos_day):
      starting_range=pos_day
      ending_range=pos_day + request.numDays + 1
      return max(occupied_tools.get((d, request.tool), 0) 
                             for d in range(starting_range, ending_range))
     
     return min(all_deleverable_days, key=score)
     
def request_placer(request, the_day_of_delivery, occupied_tools, maximum_amount_of_tools_of_type):
    """Assign delivery day and update usage."""
    the_day_of_delivery[request.ID]=obtain_optimal_day(request, occupied_tools, maximum_amount_of_tools_of_type)
    the_day_when_delivery=the_day_of_delivery[request.ID]
    occupancy_days=request.numDays + 1
    #the_day_of_delivery[request.ID] = call_optimal
    for day in range(the_day_when_delivery, the_day_when_delivery + occupancy_days):
        comb_day_with_tool_type=(day, request.tool)
        occupied_tools[comb_day_with_tool_type] += request.toolCount
# 4. Zoek alle overtredingen
def overuse(occupied_tools,list_of_tools, type_of_tool_occupied):

    all_problems = {}
    for (day, type_of_tool), utilize in occupied_tools.items():
     equal_type=(type_of_tool == type_of_tool_occupied)
     overuse_tools=(utilize > list_of_tools[type_of_tool_occupied - 1].amount)
     if equal_type and overuse_tools:
                all_problems[(day, type_of_tool_occupied)] = utilize
    return all_problems
def old_new_request(request, utilize, the_day_of_delivery, maximum_amount_of_tools):
    start = the_day_of_delivery[request.ID]
    end= start + request.numDays + 1
    
    for days in range(start, end):
       day_comb_tool_type = (days, request.tool)
       utilize[day_comb_tool_type] -= request.toolCount    
    request_placer(request, utilize, the_day_of_delivery, maximum_amount_of_tools)


def fix_a_problem(problem, utilize, the_day_of_delivery, requests, tools):
    """Try to fix one violation by shifting a random contributor."""
    day_of_problem = problem[0]    
    problem_tool = problem[1]   
    tool_max = tools[problem_tool - 1].amount
    causes = []
    for random_request_list in requests:
        equal_tool = (random_request_list.tool == problem_tool)
        request_on_problemday = (day_of_problem in range(the_day_of_delivery[random_request_list.ID], 
                                        the_day_of_delivery[random_request_list.ID] + random_request_list.numDays + 1))
        if equal_tool and request_on_problemday:
            causes.append(random_request_list)
    if not causes:
        return False
    
   # random_request_list = random.choice(causes)
    old_new_request(random.choice(causes), utilize, the_day_of_delivery, tool_max)



def assign_delivery_days(instance):
    """Assign delivery days using greedy + repair."""
    utilize = defaultdict(int)
    the_day_del = {}
    
    # Phase 1: Greedy assignment
    
    priority=lambda z: (z.toDay, z.toDay - z.fromDay)

    for i, request in enumerate (sorted(instance.Requests,
                             key=priority)):
       # tool_max = instance.Tools[request.tool - 1].amount
        request_placer(request, utilize, the_day_del, instance.Tools[request.tool - 1].amount)
    
    # Phase 2: Repair
    tries_to_repare=0
    maxum_repair_attempts=5000
    available_problem=True

    while tries_to_repare < maxum_repair_attempts:
        tries_to_repare+=1
        available_problem=False
        end_range=len(instance.Tools) + 1
        for i in range(1, end_range):
            problems = overuse(utilize, instance.Tools, i)
            if problems:
                available_problem=True
                problem=list(problems.keys())[0]  # (day, tool)
                fix_a_problem(problem, utilize, the_day_del, instance.Requests, instance.Tools)
                break

    return the_day_del  
def build_routes(inst, delivery_day):
    """
    STEP 2B — Send a separate truck for each task.

    Each truck drives: depot -> customer -> depot
    Route = [0, task, 0]   where 0 = depot

    Positive task (+r) = delivery of request r
    Negative task (-r) = pickup of request r

    This is the simplest solution that always works:
      - Never capacity issues (one task per truck)
      - Never distance issues (every customer is reachable)

    Returns: dict  day -> list of routes
    """
    day_tasks = defaultdict(list)

    for req in inst.Requests:
        deliver = delivery_day[req.ID]
        pickup  = deliver + req.numDays

        day_tasks[deliver].append(+req.ID)   # delivery
        day_tasks[pickup].append(-req.ID)    # pickup

    days_routes = {}
    for day, tasks in sorted(day_tasks.items()):
        routes = []
        for task in tasks:
            route = [0, task, 0]   # depot -> customer -> depot
            routes.append(route)
        days_routes[day] = routes

    return days_routes

# =============================================================================
# STEP 3 — Cost calculation
# =============================================================================

def compute_cost(inst, dist, delivery_day, days_routes):
    """
    STEP 3 — Calculate the total cost of the solution.

    Cost formula (from the problem):
        VEHICLE_COST      x  max vehicles used on a single day
        VEHICLE_DAY_COST  x  total vehicle-days (sum across all days)
        DISTANCE_COST     x  total travel distance
        tool[i].cost      x  peak daily usage of tool type i

    Tool usage (validator definition):
      Tools count as outside-depot from delivery day through pickup day
      inclusive: range(delivery_day, pickup_day + 1)

    Returns:
        (max_vehicles, total_vehicle_days, tool_use_list,
         total_distance, total_cost)
    """
    num_tools = len(inst.Tools)

    # ── 1. Daily tool usage ──────────────────────────────────────────
    daily = defaultdict(lambda: [0] * num_tools)

    for req in inst.Requests:
        ti      = req.tool - 1
        deliver = delivery_day[req.ID]
        pickup  = deliver + req.numDays

        for day in range(deliver, pickup + 1):   # incl. pickup day
            daily[day][ti] += req.toolCount

    # Peak per tool type
    tool_use = [0] * num_tools
    for usage in daily.values():
        for i in range(num_tools):
            tool_use[i] = max(tool_use[i], usage[i])

    # ── 2. Vehicles and distance ─────────────────────────────────────
    max_vehicles       = 0
    total_vehicle_days = 0
    total_distance     = 0

    for day, routes in days_routes.items():
        max_vehicles        = max(max_vehicles, len(routes))
        total_vehicle_days += len(routes)

        for route in routes:
            for i in range(len(route) - 1):
                stop_a = route[i]
                stop_b = route[i + 1]

                # 0 = depot, otherwise customer location of that request
                node_a = inst.DepotCoordinate if stop_a == 0 \
                         else inst.Requests[abs(stop_a) - 1].node
                node_b = inst.DepotCoordinate if stop_b == 0 \
                         else inst.Requests[abs(stop_b) - 1].node

                total_distance += dist[node_a][node_b]

    # ── 3. Total cost ────────────────────────────────────────────────
    total_cost = (
          max_vehicles       * inst.VehicleCost
        + total_vehicle_days * inst.VehicleDayCost
        + total_distance     * inst.DistanceCost
        + sum(tool_use[i] * inst.Tools[i].cost for i in range(num_tools))
    )

    return max_vehicles, total_vehicle_days, tool_use, total_distance, total_cost

# =============================================================================
# STEP 2C — Write solution
# =============================================================================

def write_solution(inst, dist, delivery_day, days_routes, output_path):
    """
    STEP 2C — Write the solution in the official tab-separated format.

    Each route is written as:
        vehicle_nr  R  0  task  0
    (values separated by tabs)

    Returns the total cost.
    """
    max_v, vdays, tool_use, distance, cost = compute_cost(
        inst, dist, delivery_day, days_routes)

    lines = [
        f"DATASET = {inst.Dataset}",
        f"NAME = {inst.Name}",
        "",
        f"MAX_NUMBER_OF_VEHICLES = {max_v}",
        f"NUMBER_OF_VEHICLE_DAYS = {vdays}",
        f"TOOL_USE = {' '.join(str(t) for t in tool_use)}",
        f"DISTANCE = {distance}",
        f"COST = {cost}",
        "",
    ]

    for day in sorted(days_routes):
        routes = days_routes[day]
        if not routes:
            continue
        lines.append(f"DAY = {day}")
        lines.append(f"NUMBER_OF_VEHICLES = {len(routes)}")
        for vi, route in enumerate(routes):
            lines.append(f"{vi + 1}\tR\t" + "\t".join(str(x) for x in route))
        lines.append("")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))

    return cost

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
    dist = calculate_all_distances(inst)

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
        print("  [Step 2B] Building routes (one truck per task)...")
    days_routes = build_routes(inst, delivery_day)

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

 