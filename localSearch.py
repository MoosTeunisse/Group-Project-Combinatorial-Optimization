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
    # Placeholder for relocate implementation
    return None

def swap(day_routes, inst, dist):
    # Placeholder for swap implementation
    return None

def two_opt(day_routes, inst, dist):
    # Placeholder for 2-opt implementation
    return None

def two_opt_star(day_routes, inst, dist):
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
    improved_bare = local_search(bare, inst, dist)
    assert improved_bare == bare, "stubs should be a no-op"
    
    restored = add_depots(improved_bare)
    assert restored == days_routes, "round-trip did not match original"
    print("Test passed.")
    
    # your test here:
    # 1. strip the depots
    # 2. add them back
    # 3. assert the result equals the original
    # 4. print something so you know it ran