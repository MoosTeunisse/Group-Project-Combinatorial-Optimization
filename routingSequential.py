"""
=============================================================================
VeRoLog 2017  —  Step 5 Routing (sequential routing)
=============================================================================

FILE STRUCTURE (place all files in the same directory):
    routingSequential.py              <-- THIS FILE
    greedyBaseline.py                
    Solver.py
    baseCVRPTWUI.py         <-- from the zip, DO NOT modify
    InstanceCVRPTWUI.py     <-- from the zip, DO NOT modify
    Validate.py             <-- from the zip, DO NOT modify

USAGE:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
    python Solver.py --batch instances/ solutions/

WHAT DOES THIS FILE DO?

    STEP 5 — Routing (sequential routing):
    this makes a sequential extramileage insertion route.
    
=============================================================================
"""

from collections import defaultdict

# =============================================================================
# Building day tasks
# =============================================================================

def build_day_tasks(inst, delivery_day):
    """Build a dictionary mapping each day to the list of tasks (pickups and deliveries) scheduled for that day."""
    
    day_tasks = defaultdict(list)
    
    for req in inst.Requests:
        deliver, pickup = delivery_day[req.ID]
        
        day_tasks[deliver].append(req.ID)
        day_tasks[pickup].append(-req.ID)
        
    return day_tasks

# =============================================================================
# Calculating route distance
# =============================================================================

def route_distance(inst, dist, route_tasks):
    """Calculate the total distance of a route given the sequence of tasks."""
    
    if len(route_tasks) == 0:
        return 0
    
    depot = inst.DepotCoordinate
    
    first_req = inst.Requests[abs(route_tasks[0]) - 1]
    total = dist[depot][first_req.node]
    
    for i in range(len(route_tasks) - 1):
        req_a = inst.Requests[abs(route_tasks[i]) - 1]
        req_b = inst.Requests[abs(route_tasks[i + 1]) - 1]
        total += dist[req_a.node][req_b.node]
    
    last_req = inst.Requests[abs(route_tasks[-1]) - 1]
    total += dist[last_req.node][depot]
    
    return total

# =============================================================================
# Load required for a route
# =============================================================================

def required_initial_load(inst, route_tasks):
    num_tools = len(inst.Tools)
    balance = [0] * num_tools
    req_load = [0] * num_tools
    
    for task in route_tasks:
        req = inst.Requests[abs(task) - 1]
        t = req.tool - 1
        k = req.toolCount
        
        if task > 0:  # delivery
            balance[t] -= k
        else:  # pickup
            balance[t] += k

        if -balance[t] > req_load[t]:
            req_load[t] = -balance[t]
    
    return req_load

def total_load_weight(inst, load_vec):
    total = 0
    for i in range(len(load_vec)):
        total += load_vec[i] * inst.Tools[i].weight
    return total

# =============================================================================
# Route feasibility checks
# =============================================================================

def route_load_feasible(inst, route_tasks):
    load = required_initial_load(inst, route_tasks)
    
    if total_load_weight(inst, load) > inst.Capacity:
        return False
    
    for task in route_tasks:
        req = inst.Requests[abs(task) - 1]
        t = req.tool - 1
        k = req.toolCount
        
        if task > 0:  # delivery
            load[t] -= k
        else:  # pickup
            load[t] += k
        
        if total_load_weight(inst, load) > inst.Capacity:
            return False
    
    return True

def is_route_feasible(inst, dist, route_tasks):
    if route_distance(inst, dist, route_tasks) > inst.MaxDistance:
        return False
    
    if not route_load_feasible(inst, route_tasks):
        return False
    
    return True

# =============================================================================
# Insertion heuristic for sequential routing
# =============================================================================

def get_insertion_penalty(inst):
    vehicle_importance = inst.VehicleCost + inst.VehicleDayCost
    distance_importance = inst.DistanceCost
    
    total = vehicle_importance + distance_importance
    if total == 0:
        return 1.0
    
    vehicle_ratio = vehicle_importance / total
    
    return vehicle_ratio

def best_insertion_in_route(inst, dist, route_tasks, task):
    """Find the best position to insert a task into a route while maintaining feasibility."""
    
    old_dist = route_distance(inst, dist, route_tasks)
    penalty_weight = get_insertion_penalty(inst)
    
    best_pos = None
    best_score = None
    
    for pos in range(len(route_tasks) + 1):
        trial = route_tasks[:pos] + [task] + route_tasks[pos:]
        
        if not is_route_feasible(inst, dist, trial):
            continue
        
        new_dist = route_distance(inst, dist, trial)
        extra = new_dist - old_dist
        
        load_vec = required_initial_load(inst, trial)
        load_weight = total_load_weight(inst, load_vec)
        
        score = extra + penalty_weight * load_weight
        
        if best_score is None or score < best_score:
            best_score = extra
            best_pos = pos
            
    return best_pos, best_score

# =============================================================================
# Pivot selection for sequential routing
# =============================================================================

def pivot_score(inst, dist, task):
    """Calculate a pivot score for a task, which can be used to prioritize tasks for insertion."""
    
    req = inst.Requests[abs(task) - 1]
    depot = inst.DepotCoordinate
    
    distance_from_depot = dist[depot][req.node]
    weight_difficulty = inst.Tools[req.tool - 1].weight * req.toolCount
    
    return distance_from_depot + 2 * weight_difficulty

def choose_pivot(inst, dist, unrouted):
    """Choose the pivot task from the set of unrouted tasks based on the highest pivot score."""
    
    best_task = None
    best_score = None
    
    for task in unrouted:
        score = pivot_score(inst, dist, task)

        if best_score is None or score > best_score:
            best_score = score
            best_task = task
    
    return best_task

# =============================================================================
# Building the sequential routes for all days
# =============================================================================

def build_routes_sequential_ex_day(inst, dist, day_tasks):
    """Build routes sequentially for a single day, given the tasks scheduled for that day."""
    unrouted = set(day_tasks)
    finished_routes = []
    
    while len(unrouted) > 0:
        pivot = choose_pivot(inst, dist, unrouted)
        current_route = [pivot]
        unrouted.remove(pivot)
        
        improved = True
        while improved and len(unrouted) > 0:
            improved = False
            best_task = None
            best_pos = None
            best_extra = None
            
            for task in unrouted:
                pos, extra = best_insertion_in_route(inst, dist, current_route, task)
                
                if pos is None:
                    continue
                
                if best_extra is None or extra < best_extra:
                    best_extra = extra
                    best_pos = pos
                    best_task = task

            if best_task is not None:
                current_route.insert(best_pos, best_task)
                unrouted.remove(best_task)
                improved = True
                
        finished_routes.append([0] + current_route + [0])  # add depot at start and end
    
    return finished_routes

def build_routes_sequential_ex(inst, delivery_day, dist):
    day_tasks = build_day_tasks(inst, delivery_day)
    days_routes = {}
    
    for day in sorted(day_tasks):
        days_routes[day] = build_routes_sequential_ex_day(inst, dist, day_tasks[day])
    
    return days_routes