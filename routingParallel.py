from routingSequential import(build_day_tasks, best_insertion_in_route, is_route_feasible, route_distance)

def build_routes_parallel(inst, dist, tasks):
    unrouted = list(tasks)
    routes = []

    while unrouted:
        best_insertion_per_task = {}  # task -> (route_idx, position, cost)
        second_best_per_task = {}     # task -> cost
        
        for task in unrouted:
            # find best and second best insertion across all routes
            ...
        
        # compute regret for each task
        # pick task with max regret
        # insert it
        # if no feasible insertion exists anywhere, open new route
    
    return [([0] + r + [0]) for r in routes]

def build_routes_parallel_regret(inst, delivery_day, dist):
    day_tasks = build_day_tasks(inst, delivery_day)
    day_routes = {}

    for day in sorted(day_tasks):
        day_routes[day] = build_routes_parallel(inst, dist, day_tasks[day])
        
    return day_routes
