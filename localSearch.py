from InstanceCVRPTWUI import InstanceCVRPTWUI
from greedyBaseline import build_dist_matrix, assign_delivery_days
from routingParallel import build_routes_parallel_regret
from routingSequential import find_route_distance, check_if_route_feasible, find_cheapest_insertion

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
                    if check_if_route_feasible(inst, dist, new_source) and check_if_route_feasible(inst, dist, new_target):
                        if source_index == target_index:
                            old_dist = find_route_distance(inst, dist, source_route)
                            new_dist = find_route_distance(inst, dist, new_target)
                            delta = (new_dist - old_dist) * inst.DistanceCost
                        else:
                            old_dist = find_route_distance(inst, dist, source_route) + find_route_distance(inst, dist, target_route)
                            new_dist = find_route_distance(inst, dist, new_source) + find_route_distance(inst, dist, new_target)
                            old_routes = (1 if source_route else 0) + (1 if target_route else 0)
                            new_routes = (1 if new_source  else 0) + (1 if new_target  else 0)
                            delta = (new_dist - old_dist) * inst.DistanceCost + (new_routes - old_routes) * inst.VehicleDayCost
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

                    new_route1 = route1[:]
                    new_route2 = route2[:]

                    new_route1[pos1] = task2
                    new_route2[pos2] = task1

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
                        
                        if not (
                            check_if_route_feasible(inst, dist, new_route1)
                            and check_if_route_feasible(inst, dist, new_route2)
                        ):
                            continue

                        old_dist = (
                            find_route_distance(inst, dist, route1)
                            + find_route_distance(inst, dist, route2)
                        )

                        new_dist = (
                            find_route_distance(inst, dist, new_route1)
                            + find_route_distance(inst, dist, new_route2)
                        )

                    delta = (new_dist - old_dist) * inst.DistanceCost

                    if delta < best_delta:
                        best_delta = delta
                        best_move = (
                            route1_index,
                            pos1,
                            route2_index,
                            pos2,
                        )

    if best_move is None:
        return None

    route1_index, pos1, route2_index, pos2 = best_move

    new_day_routes = [route[:] for route in day_routes]

    (
        new_day_routes[route1_index][pos1],
        new_day_routes[route2_index][pos2],
    ) = (
        new_day_routes[route2_index][pos2],
        new_day_routes[route1_index][pos1],
    )

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

                    if not (
                        check_if_route_feasible(inst, dist, new_route1)
                        and check_if_route_feasible(inst, dist, new_route2)
                    ):
                        continue

                    old_dist = (
                        find_route_distance(inst, dist, route1)
                        + find_route_distance(inst, dist, route2)
                    )

                    new_dist = (
                        find_route_distance(inst, dist, new_route1)
                        + find_route_distance(inst, dist, new_route2)
                    )
                    old_routes = (1 if route1     else 0) + (1 if route2     else 0)
                    new_routes = (1 if new_route1 else 0) + (1 if new_route2 else 0)
                    delta = (new_dist - old_dist) * inst.DistanceCost + (new_routes - old_routes) * inst.VehicleDayCost

                    if delta < best_delta:
                        best_delta = delta
                        best_move = (
                            route1_index,
                            route2_index,
                            cut1,
                            cut2,
                        )

    if best_move is None:
        return None

    route1_index, route2_index, cut1, cut2 = best_move

    route1 = day_routes[route1_index]
    route2 = day_routes[route2_index]

    new_day_routes = [route[:] for route in day_routes]

    new_day_routes[route1_index] = (
        route1[:cut1] + route2[cut2:]
    )

    new_day_routes[route2_index] = (
        route2[:cut2] + route1[cut1:]
    )

    return new_day_routes, best_delta

def local_search_one_day(day_routes, inst, dist):
    moves = [relocate, swap, two_opt, two_opt_star]
    while True:
        best_routes = None
        best_delta = 0   
        for move in moves:
            result = move(day_routes, inst, dist)
            if result is None:
                continue
            new_routes, delta = result
            if delta < best_delta:
                best_delta = delta
                best_routes = new_routes
        if best_routes is None:
            break
        day_routes = best_routes
    day_routes = [r for r in day_routes if len(r) > 0]
    return day_routes

def local_search(stripped_routes, inst, dist):
    improved_routes = {}
    for day, routes in stripped_routes.items():
        improved_routes[day] = local_search_one_day(routes, inst, dist)
    return improved_routes

# TESTING BLOCK - DELETE AFTER CODE IS COMPLETE AND WORKS
if __name__ == "__main__":
    instance_path = "B2.txt"

    inst = InstanceCVRPTWUI(instance_path)
    inst.calculateDistances()
    dist = build_dist_matrix(inst)

    delivery_day = assign_delivery_days(inst)
    days_routes = build_routes_parallel_regret(inst, delivery_day, dist)

    def day_cost(routes):
        distance = sum(find_route_distance(inst, dist, r) for r in routes)
        active = sum(1 for r in routes if r)
        return distance * inst.DistanceCost + active * inst.VehicleDayCost

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

    # Test swap
    print("\n--- swap single pass ---")
    total_swap = 0
    for day, routes in bare.items():
        result = swap(routes, inst, dist)
        if result is not None:
            new_routes, delta = result
            print(f"Day {day}: swap found delta = {delta:.2f}")
            total_swap += delta
        else:
            print(f"Day {day}: no improving swap move")
    print(f"Total swap single-pass improvement: {total_swap:.2f}")

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

    # Test 2-opt*
    print("\n--- 2-opt* single pass ---")
    total_2opt_star = 0
    for day, routes in bare.items():
        result = two_opt_star(routes, inst, dist)
        if result is not None:
            new_routes, delta = result
            print(f"Day {day}: 2-opt* found delta = {delta:.2f}")
            total_2opt_star += delta
        else:
            print(f"Day {day}: no improving 2-opt* move")
    print(f"Total 2-opt* single-pass improvement: {total_2opt_star:.2f}")

 # Test full driver to convergence (with task preservation check)
    print("\n--- full local search driver to convergence ---")
    total_full = 0
    all_preserved = True
    for day, routes in bare.items():
        before_tasks = sorted(t for r in routes for t in r)
        before = day_cost(routes)
        print(f"  Day {day}: starting...", flush=True)
        moves_list = [relocate, swap, two_opt, two_opt_star]
        pass_count = 0
        while True:
            pass_count += 1
            best_routes = None
            best_delta = 0
            best_move_name = None
            for move in moves_list:
                result = move(routes, inst, dist)
                if result is None:
                    continue
                new_routes, delta = result
                if delta < best_delta:
                    best_delta = delta
                    best_routes = new_routes
                    best_move_name = move.__name__
            if best_routes is None:
                break
            actual_before = day_cost(routes)
            actual_after = day_cost(best_routes)
            actual_delta = actual_after - actual_before
            mismatch = abs(actual_delta - best_delta) > 0.01
            flag = " [DELTA MISMATCH]" if mismatch else ""
            print(f"    pass {pass_count}: {best_move_name} reported={best_delta:.2f} actual={actual_delta:.2f}{flag}", flush=True)
            routes = best_routes
            if pass_count > 200:
                print(f"    ABORTING - over 200 passes", flush=True)
                break
        improved = routes
        after = day_cost(improved)
        after_tasks = sorted(t for r in improved for t in r)
        delta = after - before
        preserved = before_tasks == after_tasks
        if not preserved:
            all_preserved = False
        flag = "" if preserved else " [TASK MISMATCH]"
        print(f"Day {day}: before={before:.2f}, after={after:.2f}, delta={delta:.2f}{flag}")
        total_full += delta
    print(f"Total full-driver improvement: {total_full:.2f}")
    ref = total_relocate + total_swap + total_2opt + total_2opt_star
    print(f"Single-pass reference (sum of all four): {ref:.2f}")
    print(f"Task preservation: {'OK' if all_preserved else 'FAILED'}")