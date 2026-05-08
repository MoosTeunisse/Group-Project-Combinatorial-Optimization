from collections import defaultdict

def build_routes_sequential_ex(instance, delivery_days, distance):
    """Goes through the days in order and makes routes for each day sequentially cuz its sequential extramileage ya know"""
    jobs_for_a_day = collect_daily_tasks(instance, delivery_days)
    routes_for_days = {}
    
    for day in sorted(jobs_for_a_day):
        routes_for_days[day] = build_routes_for_day_seqEX(instance, distance, jobs_for_a_day[day])
    
    return routes_for_days

def build_routes_for_day_seqEX(instance, distance, day_tasks):
    """Takes the tasks for a day, then whilst there are still unrouted tasks it chooses a pivot and build a route around it.
    Picks a new pivot when the current route cant be improved no more, repeats until all tasks are routed."""
    unrouted_tasks = list(day_tasks)
    finished_routes = []
    chosen_pivots = []
    
    while unrouted_tasks:
        pivot = choose_pivot(instance, distance, unrouted_tasks, chosen_pivots)
        chosen_pivots.append(pivot)
        
        current_route = [pivot]
        unrouted_tasks.remove(pivot)
        
        route_improved = True
        while route_improved and len(unrouted_tasks) > 0:
            route_improved = False
            best_task = None
            best_position_task = None
            best_extra_distance = None
            
            for task in unrouted_tasks:
                position, extra_distance = find_cheapest_insertion(instance, distance, current_route, task)
                
                if position is None:
                    continue
                
                if best_extra_distance is None or extra_distance < best_extra_distance:
                    best_extra_distance = extra_distance
                    best_position_task = position
                    best_task = task

            if best_task is not None:
                current_route.insert(best_position_task, best_task)
                unrouted_tasks.remove(best_task)
                route_improved = True
                
        finished_routes.append([0] + current_route + [0]) 
    
    return finished_routes

def collect_daily_tasks(instance, delivery_days):
    """Make a dict of tasks (delivery and pickup) for the day"""
    tasks_by_day = defaultdict(list)
    
    for req in instance.Requests:
        deliver = delivery_days[req.ID]
        pickup = deliver + req.numDays
        
        tasks_by_day[deliver].append(req.ID)
        tasks_by_day[pickup].append(-req.ID)
        
    return tasks_by_day

def find_cheapest_insertion(instance, distance, route, task):
    """Find the best position to insert task into route, return the best position and the score of the insertion"""
    best_position = None
    best_extra_distance = None
    current_distance = find_route_distance(instance, distance, route)
    
    for position in range(len(route) + 1):
        trial_route = route[:position] + [task] + route[position:]
        
        if not check_if_route_feasible(instance, distance, trial_route):
            continue
        
        new_dist = find_route_distance(instance, distance, trial_route)
        extra_distance = new_dist - current_distance
        
        if best_extra_distance is None or extra_distance < best_extra_distance:
            best_extra_distance = extra_distance
            best_position = position
            
    return best_position, best_extra_distance

def find_route_distance(instance, distance, route_tasks):
    """calc the distance of a route"""
    depot = instance.DepotCoordinate
    
    if len(route_tasks) == 0:
        return 0
    
    first_request = instance.Requests[abs(route_tasks[0]) - 1]
    total = distance[depot][first_request.node]
    
    for i in range(len(route_tasks) - 1):
        req_a = instance.Requests[abs(route_tasks[i]) - 1]
        req_b = instance.Requests[abs(route_tasks[i + 1]) - 1]
        total += distance[req_a.node][req_b.node]
    
    last_req = instance.Requests[abs(route_tasks[-1]) - 1]
    total += distance[last_req.node][depot]
    
    return total

def check_if_route_feasible(instance, distance, trial_route):
    """checks if route does not go over max distance or max load"""
    if find_route_distance(instance, distance, trial_route) > instance.MaxDistance:
        return False
    
    if not check_maximum_route_load(instance, trial_route):
        return False
    
    return True

def check_maximum_route_load(instance, route_tasks):
    """check if we ever go ove capacity during the route"""
    load = find_initial_needed_tool_load(instance, route_tasks)
    
    if check_load_weight(instance, load) > instance.Capacity:
        return False
    
    for task in route_tasks:
        request = instance.Requests[abs(task) - 1]
        i = request.tool - 1
        j = request.toolCount
        
        if task > 0:
            load[i] -= j
        else:
            load[i] += j
        
        if check_load_weight(instance, load) > instance.Capacity:
            return False
    
    return True

def find_initial_needed_tool_load(instance, route_tasks):
    """figure out how much load we need at start of route"""
    number_of_tools = len(instance.Tools)
    balance = [0] * number_of_tools
    required_load = [0] * number_of_tools
    
    for task in route_tasks:
        request = instance.Requests[abs(task) - 1]
        i = request.tool - 1
        j = request.toolCount
        
        if task > 0:
            balance[i] -= j
        else:
            balance[i] += j

        if -balance[i] > required_load[i]:
            required_load[i] = -balance[i]
    
    return required_load

def check_load_weight(instance, load_vec):
    """check weight of the load"""
    total = 0
    for i in range(len(load_vec)):
        total += load_vec[i] * instance.Tools[i].weight
    return total

def calculate_pivot_score(instance, distance, task, chosen_pivots):
    """Calc pivot score by checking distance from depot, distance from already chosen pivots and "weight" of  the task aka the tool load"""
    request = instance.Requests[abs(task) - 1]
    depot = instance.DepotCoordinate
    
    distance_from_depot = distance[depot][request.node]
    weight_difficulty = instance.Tools[request.tool - 1].weight * request.toolCount
    distance_from_pivots = 0
    
    for pivot in chosen_pivots:
        pivot_request = instance.Requests[abs(pivot) - 1]
        distance_from_pivots += distance[pivot_request.node][request.node]
    
    pivot_score = 0.25 * distance_from_depot + 0.25 * distance_from_pivots + 0.5 * weight_difficulty
    
    return pivot_score

def choose_pivot(instance, distance, unrouted, chosen_pivots):
    """Choose the next pivot based on the highest pivot score"""
    best_task = None
    best_score = None
    
    for task in unrouted:
        score = calculate_pivot_score(instance, distance, task, chosen_pivots)

        if best_score is None or score > best_score:
            best_score = score
            best_task = task
    
    return best_task
