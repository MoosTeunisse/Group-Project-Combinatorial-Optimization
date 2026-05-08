def find_task_load(inst, task):
    """return load of a task"""
    req = inst.Requests[abs(task) - 1]
    tool = inst.Tools[req.tool - 1]
    return req.toolCount * tool.weight

def find_task_and_depot_distance(inst, dist, task):
    """return dist from depot to a task"""
    req = inst.Requests[abs(task) - 1]
    depot = inst.DepotCoordinate
    return dist[depot][req.node]

def extract_pivots_from_routes(inst, dist, routes):
    """given a list of routes, extract one pivot from each route"""
    pivots = []
    
    for route in routes:
        pivot = choose_pivot_from_route(inst, dist, route)
        if pivot is not None:
            pivots.append(pivot)
        
    return pivots

def choose_pivot_from_route(inst, dist, route):
    """given a route, choose on pivot task from that route"""
    route_tasks = [t for t in route if t != 0]
    
    if not route_tasks:
        return None
    
    max_load = max(find_task_load(inst, t) for t in route_tasks)
    max_depot_dist = max(find_task_and_depot_distance(inst, dist, t) for t in route_tasks)
    
    best_task = None
    best_score = None
    
    for task in route_tasks:
        score = find_task_difficulty(inst, dist, task, max_load, max_depot_dist)
        if best_score is None or score > best_score:
            best_score = score
            best_task = task
    
    return best_task

def more_objective_aware_weights(inst):
    """make weights be based on relative importance of vehicle and distance cost
       maybe thisll help with more when distance is less important since we kinda focus on that more than anything else"""
    vehicle_importance = inst.VehicleCost + inst.VehicleDayCost
    distance_importance = inst.DistanceCost
    
    total = vehicle_importance + distance_importance
    if total == 0:
        return 0.5, 0.5
    
    vehicle_ratio = vehicle_importance / total
    distance_ratio = distance_importance / total
    
    alpha = 0.2 + 0.4 * distance_ratio
    beta = 0.2 + 0.8 * vehicle_ratio
    
    return alpha, beta

def find_task_difficulty(inst, dist, task, max_load, max_depot_dist):
    """return normalized score representing the difficulty of a task:
        alpha * normalized load + beta * normalized depot distance"""
    alpha, beta = more_objective_aware_weights(inst)
    
    load = find_task_load(inst, task)
    depot_dist = find_task_and_depot_distance(inst, dist, task)
    
    dist_score = 0.0 if max_depot_dist == 0 else depot_dist / max_depot_dist
    load_score = 0.0 if max_load == 0 else load / max_load
    
    return alpha * dist_score + beta * load_score


