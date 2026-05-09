import time
from routingSequential import find_route_distance, check_if_route_feasible

def strip_depots(days_routes):
    no_depot_route = {key: [route[1:-1] for route in day_routes] for key, day_routes in days_routes.items()}
    return no_depot_route

def add_depots(days_routes):
    route_with_depot = {key: [[0] + route + [0] for route in day_routes if len(route) > 0] for key, day_routes in days_routes.items()}
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
                    
                    new_source = source_route[:source_position] + source_route[source_position+1:]

                    if source_index == target_index:
                        adjusted_target_position = target_position

                        if target_position > source_position:
                            adjusted_target_position -= 1

                        new_target = (
                            new_source[:adjusted_target_position]
                            + [task]
                            + new_source[adjusted_target_position:]
                        )

                        if not check_if_route_feasible(inst, dist, new_target):
                            continue

                        old_dist = find_route_distance(inst, dist, source_route)
                        new_dist = find_route_distance(inst, dist, new_target)
                        delta = (new_dist - old_dist) * inst.DistanceCost

                    else:
                        new_target = (
                            target_route[:target_position]
                            + [task]
                            + target_route[target_position:]
                        )

                        if not (
                            check_if_route_feasible(inst, dist, new_source)
                            and check_if_route_feasible(inst, dist, new_target)
                        ):
                            continue

                        old_dist = (
                            find_route_distance(inst, dist, source_route)
                            + find_route_distance(inst, dist, target_route)
                        )

                        new_dist = (
                            find_route_distance(inst, dist, new_source)
                            + find_route_distance(inst, dist, new_target)
                        )

                        old_routes = (1 if source_route else 0) + (1 if target_route else 0)
                        new_routes = (1 if new_source else 0) + (1 if new_target else 0)

                        delta = (
                            (new_dist - old_dist) * inst.DistanceCost
                            + (new_routes - old_routes) * inst.VehicleDayCost
                        )

                    if delta < best_delta:
                        best_delta = delta
                        best_move = (
                            source_index,
                            source_position,
                            target_index,
                            target_position
                        )
    if best_move is None:
        return None
    source_index, source_position, target_index, target_position = best_move
    new_day_routes = [route[:] for route in day_routes]
    moved_task = new_day_routes[source_index].pop(source_position)
    
    if source_index == target_index and target_position > source_position:
        target_position -= 1
    
    new_day_routes[target_index].insert(target_position, moved_task)
    return new_day_routes, best_delta

def swap(day_routes, inst, dist):
    """Best-improvement swap over one day's routes.

    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    best_delta = 0
    best_move = None

    for route1_index, route1 in enumerate(day_routes):
        for pos1 in range(len(route1)):
            task1 = route1[pos1]

            for route2_index in range(route1_index, len(day_routes)):
                route2 = day_routes[route2_index]
                start_pos2 = pos1 + 1 if route1_index == route2_index else 0

                for pos2 in range(start_pos2, len(route2)):
                    task2 = route2[pos2]

                    if route1_index == route2_index:
                        new_route1 = route1[:]
                        new_route1[pos1] = task2
                        new_route1[pos2] = task1

                        if not check_if_route_feasible(inst, dist, new_route1):
                            continue

                        old_dist = find_route_distance(inst, dist, route1)
                        new_dist = find_route_distance(inst, dist, new_route1)
                    else:
                        new_route1 = route1[:]
                        new_route2 = route2[:]
                        new_route1[pos1] = task2
                        new_route2[pos2] = task1
                        
                        if not (check_if_route_feasible(inst, dist, new_route1) and check_if_route_feasible(inst, dist, new_route2)):
                            continue

                        old_dist = (find_route_distance(inst, dist, route1) + find_route_distance(inst, dist, route2))
                        new_dist = (find_route_distance(inst, dist, new_route1) + find_route_distance(inst, dist, new_route2))
                    delta = (new_dist - old_dist) * inst.DistanceCost

                    if delta < best_delta:
                        best_delta = delta
                        best_move = (route1_index, pos1, route2_index, pos2)

    if best_move is None:
        return None

    route1_index, pos1, route2_index, pos2 = best_move
    new_day_routes = [route[:] for route in day_routes]
    (new_day_routes[route1_index][pos1], new_day_routes[route2_index][pos2],) = (new_day_routes[route2_index][pos2], new_day_routes[route1_index][pos1],)

    return new_day_routes, best_delta

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
                if check_if_route_feasible(inst, dist, new_route):
                    old_dist = find_route_distance(inst, dist, route)
                    new_dist = find_route_distance(inst, dist, new_route)
                    delta = (new_dist - old_dist) * inst.DistanceCost
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

    Exchanges route tails between two different routes.

    Returns (new_day_routes, delta) for the move that most reduces total
    distance, or None if no improving move exists.
    """
    best_delta = 0
    best_move = None

    for route1_index in range(len(day_routes)):
        for route2_index in range(route1_index + 1, len(day_routes)):
            route1 = day_routes[route1_index]
            route2 = day_routes[route2_index]

            for cut1 in range(len(route1) + 1):
                for cut2 in range(len(route2) + 1):
                    # Exchange tails
                    new_route1 = route1[:cut1] + route2[cut2:]
                    new_route2 = route2[:cut2] + route1[cut1:]

                    if not (check_if_route_feasible(inst, dist, new_route1) and check_if_route_feasible(inst, dist, new_route2)):
                        continue

                    old_dist = (find_route_distance(inst, dist, route1) + find_route_distance(inst, dist, route2))
                    new_dist = (find_route_distance(inst, dist, new_route1) + find_route_distance(inst, dist, new_route2))
                    old_routes = (1 if route1     else 0) + (1 if route2     else 0)
                    new_routes = (1 if new_route1 else 0) + (1 if new_route2 else 0)
                    delta = (new_dist - old_dist) * inst.DistanceCost + (new_routes - old_routes) * inst.VehicleDayCost

                    if delta < best_delta:
                        best_delta = delta
                        best_move = (route1_index, route2_index, cut1, cut2,)

    if best_move is None:
        return None
    
    route1_index, route2_index, cut1, cut2 = best_move
    route1 = day_routes[route1_index]
    route2 = day_routes[route2_index]
    new_day_routes = [route[:] for route in day_routes]
    new_day_routes[route1_index] = (route1[:cut1] + route2[cut2:])
    new_day_routes[route2_index] = (route2[:cut2] + route1[cut1:])
    return new_day_routes, best_delta

def local_search_one_day(day_routes, inst, dist, max_seconds = 5.0, max_iterations = 5000):
    moves = [relocate, swap, two_opt, two_opt_star]
    start_time = time.time()
    iterations = 0
    
    while True:
        if time.time() - start_time > max_seconds:
            break
        if iterations >= max_iterations:
            break
        
        iterations += 1
        
        best_routes = None
        best_delta = 0  
        
        for move in moves:
            if time.time() - start_time > max_seconds:
                break
            
            result = move(day_routes, inst, dist)
            if result is None:
                continue
            
            new_routes, delta = result
            
            if delta < best_delta:
                best_delta = delta
                best_routes = new_routes
        if best_routes is None:
            print(f"  No improving move found after {iterations} iterations and {time.time() - start_time:.2f} seconds.")
            break
        
        day_routes = best_routes
    day_routes = [r for r in day_routes if len(r) > 0]
    return day_routes

def local_search(stripped_routes, inst, dist, max_seconds=1.0, max_iterations=1000):
    improved_routes = {}
    for day, routes in stripped_routes.items():
        print(f"  Local Search day: {day}", flush=True)
        improved_routes[day] = local_search_one_day(routes, inst, dist, max_seconds=max_seconds, max_iterations=max_iterations)
    return improved_routes