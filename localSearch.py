from InstanceCVRPTWUI import InstanceCVRPTWUI
from greedyBaseline import build_dist_matrix, assign_delivery_days
from routingParallel import build_routes_parallel_regret

def strip_depots(days_routes):
    no_depot_route = {key: [route[1:-1] for route in day_routes] for key, day_routes in days_routes.items()}
    return no_depot_route

def add_depots(days_routes):
    route_with_depot = {key: [[0] + route + [0] for route in day_routes] for key, day_routes in days_routes.items()}
    return route_with_depot

def relocate(days_route, inst, dist):
    # Placeholder for relocate implementation
    return False

def swap(days_route, inst, dist):
    # Placeholder for swap implementation
    return False

def two_opt(days_route, inst, dist):
    # Placeholder for 2-opt implementation
    return False

def two_opt_star(day_routes, inst, dist):
    # Placeholder for 2-opt* implementation
    return False

def local_search_one_day(day_routes, inst, dist):
    # Placeholder for local search implementation
    # You can implement 2-opt, swap, or any other local search heuristic here
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


if __name__ == "__main__":
    instance_path = "B1.txt"
    
    inst = InstanceCVRPTWUI(instance_path)
    inst.calculateDistances()
    dist = build_dist_matrix(inst)
    
    delivery_day = assign_delivery_days(inst)
    days_routes = build_routes_parallel_regret(inst, delivery_day, dist)
    stripped_routes = strip_depots(days_routes)
    added_depot_routes = add_depots(stripped_routes)
    if added_depot_routes == days_routes:
        print("Test passed: Stripping and adding depots returns original routes.")
    else:
        print("Test FAILED: round-trip did not match original.")
    
    # your test here:
    # 1. strip the depots
    # 2. add them back
    # 3. assert the result equals the original
    # 4. print something so you know it ran