from InstanceCVRPTWUI import InstanceCVRPTWUI
from greedyBaseline import build_dist_matrix, assign_delivery_days
from routingParallel import build_routes_parallel_regret
from routingSequential import route_distance, is_route_feasible, best_insertion_in_route

def strip_depots(days_routes):
    no_depot_route = {key: [route[1:-1] for route in day_routes] for key, day_routes in days_routes.items()}
    return no_depot_route

def add_depots(days_routes):
    route_with_depot = {key: [[0] + route + [0] for route in day_routes] for key, day_routes in days_routes.items()}
    return route_with_depot

def relocate(day_routes, inst, dist):
    """Best-improvement relocate over one day's routes.
    
    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    best_delta = 0
    best_move = None
    for source_index, source_route in enumerate(day_routes):
        for source_position in range(len(source_route)):
            task = source_route[source_position]
            for target_index, target_route in enumerate(day_routes):
                for target_position in range(len(target_route) + 1):
                    if source_index == target_index and target_position == source_position:
                        continue
                    # Try relocating task to target route
                    new_source = source_route[:source_position] + source_route[source_position+1:]
                    if source_index == target_index:
                        base_target = new_source
                    else:
                        base_target = target_route
                    new_target = base_target[:target_position] + [task] + base_target[target_position:]
                    if is_route_feasible(inst, dist, new_source) and is_route_feasible(inst, dist, new_target):
                        if source_index == target_index:
                            old_cost = route_distance(inst, dist, source_route)
                            new_cost = route_distance(inst, dist, new_target)
                        else:
                            old_cost = route_distance(inst, dist, source_route) + route_distance(inst, dist, target_route)
                            new_cost = route_distance(inst, dist, new_source) + route_distance(inst, dist, new_target)
                        delta = new_cost - old_cost
                        if delta < best_delta:
                            best_delta = delta
                            best_move = (source_index, source_position, target_index, target_position)
    if best_move is None:
        return None
    source_index, source_position, target_index, target_position = best_move
    new_day_routes = [route[:] for route in day_routes]
    moved_task = new_day_routes[source_index].pop(source_position)
    new_day_routes[target_index].insert(target_position, moved_task)
    return new_day_routes, best_delta

def swap(day_routes, inst, dist):
    """Best-improvement swap over one day's routes.
    
    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    # Placeholder for swap implementation
    return None

def two_opt(day_routes, inst, dist):
    """Best-improvement 2-opt over one day's routes.
    
    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    best_delta = 0
    best_move = None
    for route_index, route in enumerate(day_routes):
        for i in range(len(route) - 1):
            for j in range(i + 2, len(route) + 1):
                new_route = route[:i] + route[i:j][::-1] + route[j:]
                if is_route_feasible(inst, dist, new_route):
                    old_cost = route_distance(inst, dist, route)
                    new_cost = route_distance(inst, dist, new_route)
                    delta = new_cost - old_cost
                    if delta < best_delta:
                        best_delta = delta
                        best_move = (route_index, i, j)
    if best_move is None:
        return None
    route_index, i, j = best_move
    new_day_routes = [route[:] for route in day_routes]
    target = new_day_routes[route_index]
    new_day_routes[route_index] = target[:i] + target[i:j][::-1] + target[j:]
    return new_day_routes, best_delta

def two_opt_star(day_routes, inst, dist):
    """Best-improvement 2-opt* over one day's routes.
    
    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    # Placeholder for 2-opt* implementation
    return None

def local_search_one_day(day_routes, inst, dist):
    # Placeholder for local search implementation
    moves = [relocate, swap, two_opt, two_opt_star]
    improved = True
    while improved:
        improved = False
        for move in moves:
            result = move(day_routes, inst, dist)
            if result is not None:
                new_routes, delta = result
                day_routes = new_routes
                improved = True
                break  # If we made an improvement, start over with the first move
    return day_routes

def local_search(stripped_routes, inst, dist):
    improved_routes = {}
    for day, routes in stripped_routes.items():
        improved_routes[day] = local_search_one_day(routes, inst, dist)
    return improved_routes

if __name__ == "__main__":
    instance_path = "B1.txt"
    
    inst = InstanceCVRPTWUI(instance_path)
    inst.calculateDistances()
    dist = build_dist_matrix(inst)
    
    delivery_day = assign_delivery_days(inst)
    days_routes = build_routes_parallel_regret(inst, delivery_day, dist)
    
    bare = strip_depots(days_routes)
    
    # Test relocate
    print("--- relocate single pass ---")
    total_relocate = 0
    for day, routes in bare.items():
        result = relocate(routes, inst, dist)
        if result is not None:
            new_routes, delta = result
            print(f"Day {day}: relocate found delta = {delta:.2f}")
            total_relocate += delta
        else:
            print(f"Day {day}: no improving relocate move")
    print(f"Total relocate single-pass improvement: {total_relocate:.2f}")
    
    # Test two_opt
    print("\n--- 2-opt single pass ---")
    total_2opt = 0
    for day, routes in bare.items():
        result = two_opt(routes, inst, dist)
        if result is not None:
            new_routes, delta = result
            print(f"Day {day}: 2-opt found delta = {delta:.2f}")
            total_2opt += delta
        else:
            print(f"Day {day}: no improving 2-opt move")
    print(f"Total 2-opt single-pass improvement: {total_2opt:.2f}")