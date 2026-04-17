def task_load(inst, task):
    """Return the load of a task."""
    req = inst.Requests[abs(task) - 1]
    tool = inst.Tools[req.tool - 1]
    return req.toolCount * tool.weight

def task_depot_distance(inst, dist, task):
    """Return the distance from the depot to the task."""
    req = inst.Requests[abs(task) - 1]
    depot = inst.DepotCoordinate
    return dist[depot][req.node]

def objective_aware_weights(inst):
    vehicle_importance = inst.VehicleCost + inst.VehicleDayCost
    distance_importance = inst.DistanceCost
    
    total = vehicle_importance + distance_importance
    if total == 0:
        return 0.5, 0.5
    
    vehicle_ratio = vehicle_importance / total
    distance_ratio = distance_importance / total
    
    a = 0.2 + 0.6 * distance_ratio
    b = 0.2 + 0.6 * vehicle_ratio
    
    return a,b

def task_difficulty_score(inst, dist, task, max_load, max_depot_dist):
    """Return a normalized score representing the difficulty of a task.
        alpha * normalized load + beta * normalized depot distance
    """
    a,b = objective_aware_weights(inst)
    
    load = task_load(inst, task)
    depot_dist = task_depot_distance(inst, dist, task)
    
    load_score = 0.0 if max_load == 0 else load / max_load
    dist_score = 0.0 if max_depot_dist == 0 else depot_dist / max_depot_dist
    
    return a * load_score + b * dist_score

def choose_route_pivot(inst, dist, route):
    """given a route, choose on pivot task from that route"""
    #remove depot from route
    route_tasks = [t for t in route if t != 0]
    
    if not route_tasks:
        return None
    
    max_load = max(task_load(inst, t) for t in route_tasks)
    max_depot_dist = max(task_depot_distance(inst, dist, t) for t in route_tasks)
    
    best_task = None
    best_score = None
    
    for task in route_tasks:
        score = task_difficulty_score(inst, dist, task, max_load, max_depot_dist)
        if best_score is None or score > best_score:
            best_score = score
            best_task = task
    
    return best_task

def extract_pivots_from_routes(inst, dist, routes):
    """given a list of routes, extract one pivot from each route"""
    
    pivots = []
    
    for route in routes:
        pivot = choose_route_pivot(inst, dist, route)
        if pivot is not None:
            pivots.append(pivot)
        
    return pivots