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
        new_total=occupied_tools.get(comb_day_with_tool_type, 0) + request.toolCount
        occupied_tools[comb_day_with_tool_type] = new_total
# 4. Zoek alle overtredingen
def overuse(occupied_tools,list_of_tools, type_of_tool_occupied):

    all_problems = {}
    for (day, type_of_tool), utilize_user in occupied_tools.items():
     equal_type=(type_of_tool == type_of_tool_occupied)
     overuse_tools=(utilize_user > list_of_tools[type_of_tool_occupied - 1].amount)
     if equal_type and overuse_tools:
                all_problems[(day, type_of_tool_occupied)] = utilize_user
    return all_problems

def old_new_request(request, utilize, the_day_of_delivery, maximum_amount_of_tools):
    start = the_day_of_delivery[request.ID]
    end= start + request.numDays + 1
    
    for days in range(start, end):
       day_comb_tool_type = (days, request.tool)
       utilize[day_comb_tool_type] -= request.toolCount    
    request_placer(request,the_day_of_delivery, utilize,  maximum_amount_of_tools)


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
        request_placer(request,the_day_del, utilize,  instance.Tools[request.tool - 1].amount)
    
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
def maker_of_routes(instance, the_day_of_delivery):

    delivery_pickup = defaultdict(list)

    amount_of_the_requests=len(instance.Requests)
    for i in range(amount_of_the_requests):

        req_equals_with_id=instance.Requests[i].ID
        delivery_pickup[the_day_of_delivery[req_equals_with_id]].append(+req_equals_with_id)  
        delivery_pickup[the_day_of_delivery[req_equals_with_id] + instance.Requests[i].numDays].append(-req_equals_with_id)   



    route=lambda job: [0, job, 0]
    route_every_time=lambda job_on_day: [route(job) for job in job_on_day]
    order_pickup= sorted(delivery_pickup.items())
    return {
    d: route_every_time(jobs)
    for d, jobs in order_pickup 
}

# =============================================================================
# STEP 3 — Cost calculation
# =============================================================================

def how_many_tooltype_busyday(instance, the_day_of_delivery):
    """Calculate peak tool usage per tool type."""
   # num_tools = len(instance.Tools)
    dic_keep_run_tooltype = defaultdict(lambda: [0] * len(instance.Tools))
    
    for i in range(len(instance.Requests)):
        #req = instance.Requests[i]
        #ti = instance.Requests[i].tool - 1
        #deliver = the_day_of_delivery[instance.Requests[i].ID]
        #pickup = the_day_of_delivery[instance.Requests[i].ID] + instance.Requests[i].numDays
        am_of_days=len(list(range(the_day_of_delivery[instance.Requests[i].ID],
                                       the_day_of_delivery[instance.Requests[i].ID] )))
        for j in range (am_of_days+ instance.Requests[i].numDays + 1):
                     cal_day = list(range(the_day_of_delivery[instance.Requests[i].ID], 
                      the_day_of_delivery[instance.Requests[i].ID]
                              + instance.Requests[i].numDays + 1))[j]
                     dic_keep_run_tooltype[cal_day][instance.Requests[i].tool - 1] += instance.Requests[i].toolCount

    
    return [max(dic_keep_run_tooltype[d][i] for d in dic_keep_run_tooltype) for i in range(len(instance.Tools))]


def aquire_statistics_veh(instance, distance, route_of_given_day):
    """Calculate max vehicles, total vehicle days, and total distance."""
    biggest_am_of_veh = 0
    veh_all_in_total = 0
    aquire_totaldis = 0
     
    dic_route=list(route_of_given_day.items())
    counter=0
    while counter < len(dic_route):
        #day=dic_route[counter][0]
        trip=dic_route[counter][1]
        biggest_am_of_veh = max(biggest_am_of_veh, len(trip))
        veh_all_in_total += len(trip)
        
        routes_within_day=0
        while routes_within_day < len(trip):
            route=trip[routes_within_day] 
            teller_when_stop=0
            while teller_when_stop < len(trip[routes_within_day] ) - 1:    
                the_stop_now = trip[routes_within_day] [teller_when_stop]
                followed_stop = trip[routes_within_day] [teller_when_stop + 1]
                if the_stop_now == 0:
                    loc_stop_now = instance.DepotCoordinate
                else:   
                        loc_stop_now = instance.Requests[abs(the_stop_now) - 1].node
                if followed_stop == 0:
                        loc_followed_stop = instance.DepotCoordinate               
                else:   
                        loc_followed_stop = instance.Requests[abs(followed_stop) - 1].node

                
                aquire_totaldis += distance[loc_stop_now][loc_followed_stop]
                teller_when_stop += 1
            routes_within_day += 1
        counter += 1
    return biggest_am_of_veh, veh_all_in_total, aquire_totaldis


def final_calculate_all_costs(instance, distance, the_day_of_delivery, route_of_given_day):

    max_of_tool = how_many_tooltype_busyday(instance, the_day_of_delivery)
    
    # Step 2: Vehicle stats
    biggest_am_of_veh, veh_all_in_total, aquire_totaldis = aquire_statistics_veh(instance, distance, route_of_given_day)
    
    # Step 3: Total cost
# Kosten opsplitsen in 4 delen
    cal_cost_of_veh_given_day = veh_all_in_total * instance.VehicleDayCost
    cal_cost_distance_total = aquire_totaldis * instance.DistanceCost
    cal_cost_of_veh = biggest_am_of_veh * instance.VehicleCost
    total_cost_for_tools = 0
    for i in range(len(instance.Tools)):
        total_cost_for_tools =total_cost_for_tools+ max_of_tool[i] * instance.Tools[i].cost
   # Totaal
    cal_all_costs_total = cal_cost_of_veh_given_day +cal_cost_distance_total +cal_cost_of_veh +total_cost_for_tools     
    res_biggest_am_of_veh=biggest_am_of_veh
    res_veh_all_in_total=veh_all_in_total
    res_max_of_tool=max_of_tool
    res_aquire_totaldis=aquire_totaldis
    res_cal_all_costs_total=cal_all_costs_total
    res=res_biggest_am_of_veh, res_veh_all_in_total, res_max_of_tool, res_aquire_totaldis, res_cal_all_costs_total
    
    return res
# =============================================================================
# STEP 2C — Write solution
# =============================================================================

def fun_sol_output_writer(instance, distance, the_day_of_delivery, route_of_given_day, file_referrer):

    res = final_calculate_all_costs(instance, distance, the_day_of_delivery, route_of_given_day)
  #  res_biggest_am_of_veh, res_veh_all_in_total, res_max_of_tool, res_aquire_totaldis, res_cal_all_costs_total = res

    sol_line_by_line = [
        f"DATASET = {instance.Dataset}",
        f"NAME = {instance.Name}",
        "",
        f"MAX_NUMBER_OF_VEHICLES = {res[0]}",
        f"NUMBER_OF_VEHICLE_DAYS = {res[1]}",
        f"TOOL_USE = {' '.join(str(z) for z in res[2])}",
        f"DISTANCE = {res[3]}",
        f"COST = {res[4]}",
        "",]

    given_day_sor=sorted(route_of_given_day)
    for i in range(len(given_day_sor)):
        this_moment_day = given_day_sor[i]
        trips = route_of_given_day[this_moment_day]
        checker_trip=len(trips) > 0
        if checker_trip:
            sol_line_by_line+=[f"DAY = {this_moment_day}",f"NUMBER_OF_VEHICLES = {len(trips)}"]
            for i in range(len(trips)):
                trip = trips[i]
                string_maker_trip="\t".join(str(q) for q in trip)
                output_line_maker=f"{i + 1}\tR\t{string_maker_trip}"
                sol_line_by_line.append(output_line_maker)
            sol_line_by_line.append("")



    os.makedirs(os.path.dirname(file_referrer), exist_ok=True) if os.path.dirname(file_referrer) else None
    with open(file_referrer, 'w') as g:
     text_outputter="\n".join(sol_line_by_line)
     g.write(text_outputter)
    return res[4]

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
    days_routes = maker_of_routes(inst, delivery_day)

    if verbose:
        print("  [Step 2C] Writing solution...")
    cost = fun_sol_output_writer(inst, dist, delivery_day, days_routes, output_path)

    if verbose:
        max_v, vdays, tool_use, distance, _ = final_calculate_all_costs(
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

 