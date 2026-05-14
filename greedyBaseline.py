import math
import os
import random
import copy
from collections import defaultdict

def calculate_all_distances(instance_data):
    all_locations=instance_data.Coordinates
    amount_of_locations=len(all_locations)
    row_with_zero=[0] * amount_of_locations
    distance_table = [row_with_zero[:] for _ in range(amount_of_locations)]
    for i in range(amount_of_locations):
        for j in range(i + 1, amount_of_locations):
            firstX, firstY=all_locations[i].X, all_locations[i].Y
            secondX, secondY=all_locations[j].X, all_locations[j].Y
            difference_X=firstX- secondX
            difference_Y= firstY- secondY

            distance  = int(math.floor(math.sqrt((difference_X) ** 2 + 
                                            (difference_Y) ** 2)))
            distance_table[i][j] = distance
            distance_table[j][i] = distance
    return distance_table

def possible_on_day(request, given_day, occupied_tools, maximum_amount_of_tools_of_type):
    last_day=given_day + request.numDays + 1
    for day in range(given_day, last_day):
        total_amount_of_tools_of_type=occupied_tools.get((day, request.tool),0) + request.toolCount
        if total_amount_of_tools_of_type > maximum_amount_of_tools_of_type:
            return False
    return True

def obtain_optimal_day(request, occupied_tools, maximum_amount_of_tools_of_type):
    """Find earliest feasible day, or day with lowest peak."""
    starting_day=request.fromDay
    ending_day=request.toDay + 1
    for day in range(starting_day, ending_day):
        if possible_on_day(request, day, occupied_tools, maximum_amount_of_tools_of_type):
            return day
    else:
     all_deleverable_days=range(request.fromDay, request.toDay + 1)
     def score(pos_day):
      starting_range=pos_day
      ending_range=pos_day + request.numDays + 1
      return max(occupied_tools.get((d, request.tool), 0) 
                             for d in range(starting_range, ending_range))
     
     return min(all_deleverable_days, key=score)

def request_placer(request, the_day_of_delivery, occupied_tools, maximum_amount_of_tools_of_type):
    the_day_of_delivery[request.ID]=obtain_optimal_day(request, occupied_tools, maximum_amount_of_tools_of_type)
    the_day_when_delivery=the_day_of_delivery[request.ID]
    occupancy_days=request.numDays + 1
    for day in range(the_day_when_delivery, the_day_when_delivery + occupancy_days):
        comb_day_with_tool_type=(day, request.tool)
        new_total=occupied_tools.get(comb_day_with_tool_type, 0) + request.toolCount
        occupied_tools[comb_day_with_tool_type] = new_total

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
    
    old_new_request(random.choice(causes), utilize, the_day_of_delivery, tool_max)

def assign_delivery_days(instance):
    """Assign delivery days using greedy + repair."""
    utilize = defaultdict(int)
    the_day_del = {}

    priority=lambda z: (z.toDay, z.toDay - z.fromDay)

    for i, request in enumerate (sorted(instance.Requests,
                             key=priority)):
        request_placer(request,the_day_del, utilize,  instance.Tools[request.tool - 1].amount)

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
                problem=list(problems.keys())[0]
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

def compute_cost(inst, dist, days_routes):
    num_tools = len(inst.Tools)
    tool_use = compute_tool_use_exact_validator(inst, days_routes)

    max_vehicles = 0
    total_vehicle_days = 0
    total_distance = 0

    for day,routes in days_routes.items():
        max_vehicles = max(max_vehicles, len(routes))
        total_vehicle_days += len(routes)

        for route in routes:
            for i in range(len(route) - 1):
                current_stop = route[i]
                next_stop = route[i + 1]

                if current_stop == 0:
                    node_current_stop = inst.DepotCoordinate
                else:
                    node_current_stop = inst.Requests[abs(current_stop) - 1].node
                
                if next_stop == 0:
                    node_next_stop = inst.DepotCoordinate
                else:
                    node_next_stop = inst.Requests[abs(next_stop) - 1].node
                
                total_distance += dist[node_current_stop][node_next_stop]

    tool_cost =sum(tool_use[i] * inst.Tools[i].cost for i in range(num_tools))
    
    total_cost = (max_vehicles * inst.VehicleCost + total_vehicle_days * inst.VehicleDayCost + total_distance * inst.DistanceCost + tool_cost)

    return max_vehicles, total_vehicle_days, tool_use, total_distance, total_cost

def compute_tool_use_exact_validator(inst, days_routes):
    """Exact copy of the validator's tool-use logic"""
    toolStatus = [0] * len(inst.Tools)
    toolUse = [0] * len(inst.Tools)

    for dayNumber in range(1, inst.Days + 1):
        routes = days_routes.get(dayNumber, [])

        day_calcStartDepot = [0] * len(inst.Tools)
        day_calcFinishDepot = [0] * len(inst.Tools)

        for route in routes:
            currentTools = [0] * len(inst.Tools)
            depotVisits = [[0] * len(inst.Tools)]
            nodeVisits = []
            lastNode = None

            for node in route:
                if node == 0:
                    if lastNode is not None:
                        bringTools = [0] * len(inst.Tools)
                        sumTools = [0] * len(inst.Tools)

                        for tools in nodeVisits:
                            sumTools = [max(x) for x in zip(tools, sumTools)]
                            bringTools = [min(x) for x in zip(bringTools, tools)]
                            sumTools = [max(0, a) for a in sumTools]

                        depotVisits[-1] = [sum(x) for x in zip(bringTools, depotVisits[-1])]
                        depotVisits.append([b - a for a, b in zip(bringTools, nodeVisits[-1])])

                        currentTools = [0] * len(inst.Tools)
                        nodeVisits = []

                elif node > 0:
                    req = inst.Requests[node - 1]
                    currentTools[req.tool - 1] -= req.toolCount

                elif node < 0:
                    node = -node
                    req = inst.Requests[node - 1]
                    currentTools[req.tool - 1] += req.toolCount

                nodeVisits.append(copy.copy(currentTools))
                lastNode = node

            visitTotal = [0] * len(inst.Tools)
            totalUsedAtStart = [0] * len(inst.Tools)

            for visit in depotVisits:
                visitTotal = [sum(x) for x in zip(visit, visitTotal)]
                totalUsedAtStart = [b - min(0, a) for a, b in zip(visitTotal, totalUsedAtStart)]
                visitTotal = [max(0, a) for a in visitTotal]

            day_calcStartDepot = [b - a for a, b in zip(totalUsedAtStart, day_calcStartDepot)]
            day_calcFinishDepot = [b + a for a, b in zip(visitTotal, day_calcFinishDepot)]

        toolStatus = [sum(x) for x in zip(toolStatus, day_calcStartDepot)]
        toolUse = [max(-a, b) for a, b in zip(toolStatus, toolUse)]
        toolStatus = [sum(x) for x in zip(toolStatus, day_calcFinishDepot)]

    return toolUse

def fun_sol_output_writer(instance, distance, the_day_of_delivery, route_of_given_day, file_referrer):

    res = compute_cost(instance, distance, route_of_given_day)

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
