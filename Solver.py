import math
import os
import argparse
import random
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

def processor(txt_finder, sol_txt):
    object_data = InstanceCVRPTWUI(txt_finder)
    checker=object_data.isValid()
    if checker:
        #object_data.calculateDistances()
        cal_distances = calculate_all_distances(object_data)
        ass_del = assign_delivery_days(object_data)
        mak_of_routes = maker_of_routes(object_data, ass_del)
   # fun_sol_output_writer(inst, dist, delivery_day, days_routes, output_path)
        ret_parameters=(object_data, cal_distances, ass_del, mak_of_routes, sol_txt)
        return fun_sol_output_writer(ret_parameters[0], ret_parameters[1], ret_parameters[2], ret_parameters[3], ret_parameters[4])

    else:
        return None

def main():
    arg_p = argparse.ArgumentParser()
       
    arg_p.add_argument('-i', '--inp', required=True)
    arg_p.add_argument('-s', '--solution')


    a    = arg_p.parse_args()

    #output = a.output or a.instance.replace('.txt', '_solution.txt')
    processor(a.inp, a.solution or a.inp.replace('.txt', '_res.txt'))
       
if __name__ == '__main__':
    main()

 