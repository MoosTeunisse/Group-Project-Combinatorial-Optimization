from collections import defaultdict

def build_routes_sequential_ex(inst, delivery_day, dist):
    """Goes through the days in order and makes routes for each day sequentially cuz its sequential extramileage ya know"""
    day_tasks = build_day_tasks(inst, delivery_day)
    days_routes = {}
    
    for day in sorted(day_tasks):
        days_routes[day] = build_routes_sequential_ex_day(inst, dist, day_tasks[day])
    
    return days_routes

def build_routes_sequential_ex_day(inst, dist, day_tasks):
    """Takes the tasks for a day, then whilst there are still unrouted tasks it chooses a pivot and build a route around it.
    Picks a new pivot when the current route cant be improved no more, repeats until all tasks are routed."""
    unrouted_tasks = list(day_tasks)
    finished_routes = []
    chosen_pivots = []
    
    #keep going until all tasks are routed
    while unrouted_tasks:
        #pick the best pivot from the unrouted tasks
        current_pivot = choose_pivot(inst, dist, unrouted_tasks, chosen_pivots)
        chosen_pivots.append(current_pivot)
        
        current_route = [current_pivot]
        unrouted_tasks.remove(current_pivot)
        
        #keep adding tasks to the current route until adding a tasks doesnt improve it no more
        improved = True
        while improved and len(unrouted_tasks) > 0:
            improved = False
            best_task = None
            best_position = None
            best_extra = None
            
            for task in unrouted_tasks:
                position, extra = best_insertion_in_route(inst, dist, current_route, task)
                
                if position is None:
                    continue
                
                if best_extra is None or extra < best_extra:
                    best_extra = extra
                    best_position = position
                    best_task = task

            #insert best task and mark as improved
            if best_task is not None:
                current_route.insert(best_position, best_task)
                unrouted_tasks.remove(best_task)
                improved = True
                
        #add the route plus the depot at start and end
        finished_routes.append([0] + current_route + [0]) 
    
    return finished_routes

def build_day_tasks(inst, delivery_day):
    """Make a dict of tasks (delivery and pickup) for the day"""
    day_tasks = defaultdict(list)
    
    for req in inst.Requests:
        deliver = delivery_day[req.ID]
        pickup = deliver + req.numDays
        
        day_tasks[deliver].append(req.ID)
        day_tasks[pickup].append(-req.ID)
        
    return day_tasks

def best_insertion_in_route(inst, dist, route_tasks, task):
    """Find the best position to insert task into route, return the best position and the score of the insertion"""
    old_dist = route_distance(inst, dist, route_tasks)
    
    best_position = None
    best_score = None
    
    for pos in range(len(route_tasks) + 1):
        trial_route = route_tasks[:pos] + [task] + route_tasks[pos:]
        
        if not is_route_feasible(inst, dist, trial_route):
            continue
        
        new_dist = route_distance(inst, dist, trial_route)
        extra_distance = new_dist - old_dist
        
        if best_score is None or extra_distance < best_score:
            best_score = extra_distance
            best_position = pos
            
    return best_position, best_score

def route_distance(inst, dist, route_tasks):
    """calc the distance of a route"""
    depot = inst.DepotCoordinate
    
    if len(route_tasks) == 0:
        return 0
    
    first_request = inst.Requests[abs(route_tasks[0]) - 1]
    total = dist[depot][first_request.node]
    
    for i in range(len(route_tasks) - 1):
        req_a = inst.Requests[abs(route_tasks[i]) - 1]
        req_b = inst.Requests[abs(route_tasks[i + 1]) - 1]
        total += dist[req_a.node][req_b.node]
    
    last_req = inst.Requests[abs(route_tasks[-1]) - 1]
    total += dist[last_req.node][depot]
    
    return total

def is_route_feasible(inst, dist, route_tasks):
    """checks if route does not go over max distance or max load"""
    if route_distance(inst, dist, route_tasks) > inst.MaxDistance:
        return False
    
    if not check_maximum_route_load(inst, route_tasks):
        return False
    
    return True

def check_maximum_route_load(inst, route_tasks):
    """check if we ever go ove capacity during the route"""
    load = required_initial_load(inst, route_tasks)
    
    if total_load_weight(inst, load) > inst.Capacity:
        return False
    
    for task in route_tasks:
        req = inst.Requests[abs(task) - 1]
        t = req.tool - 1
        k = req.toolCount
        
        if task > 0:
            load[t] -= k
        else:
            load[t] += k
        
        if total_load_weight(inst, load) > inst.Capacity:
            return False
    
    return True

def required_initial_load(inst, route_tasks):
    """figure out how much load we need at start of route"""
    num_tools = len(inst.Tools)
    balance = [0] * num_tools
    req_load = [0] * num_tools
    
    for task in route_tasks:
        req = inst.Requests[abs(task) - 1]
        t = req.tool - 1
        k = req.toolCount
        
        if task > 0:
            balance[t] -= k
        else:
            balance[t] += k

        if -balance[t] > req_load[t]:
            req_load[t] = -balance[t]
    
    return req_load

def total_load_weight(inst, load_vec):
    """check weight of the load"""
    total = 0
    for i in range(len(load_vec)):
        total += load_vec[i] * inst.Tools[i].weight
    return total

def pivot_score(inst, dist, task, chosen_pivots):
    """Calc pivot score by checking distance from depot, distance from already chosen pivots and "weight" of  the task aka the tool load"""
    req = inst.Requests[abs(task) - 1]
    depot = inst.DepotCoordinate
    
    distance_from_depot = dist[depot][req.node]
    weight_difficulty = inst.Tools[req.tool - 1].weight * req.toolCount
    distance_from_pivots = 0
    
    for pivot in chosen_pivots:
        pivot_request = inst.Requests[abs(pivot) - 1]
        distance_from_pivots += dist[pivot_request.node][req.node]
    
    pivot_score = 0.25 * distance_from_depot + 0.25 * distance_from_pivots + 0.5 * weight_difficulty
    
    return pivot_score

def choose_pivot(inst, dist, unrouted, chosen_pivots):
    """Choose the next pivot based on the highest pivot score"""
    best_task = None
    best_score = None
    
    for task in unrouted:
        score = pivot_score(inst, dist, task, chosen_pivots)

        if best_score is None or score > best_score:
            best_score = score
            best_task = task
    
    return best_task
