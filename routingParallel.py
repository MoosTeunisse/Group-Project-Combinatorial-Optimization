from routingSequential import(build_day_tasks, best_insertion_in_route, is_route_feasible, route_distance)

def build_routes_parallel(inst, dist, task_list):
    unrouted = list(task_list)
    routes = []

    while unrouted:
        best_insertion_per_task, second_best_insertion_per_task = scan_insertions(inst, dist, unrouted, routes)
        # Check if routes match the number of unrouted tasks, if not add an empty route and restart
        if len(best_insertion_per_task) < len(unrouted):
            routes.append([])
            continue
        
        chosen_task = select_task(best_insertion_per_task, second_best_insertion_per_task, unrouted)
        chosen_r, chosen_p, chosen_cost = best_insertion_per_task[chosen_task]
        routes[chosen_r].insert(chosen_p, chosen_task)
        unrouted.remove(chosen_task)
    return [([0] + r + [0]) for r in routes]

def scan_insertions(inst, dist, unrouted, routes):
    best_insertion_per_task = {}  # task -> (route_idx, position, cost)
    second_best_insertion_per_task = {}     # task -> cost
    # find best and second best insertion across all routes
    for task in unrouted:
        best_cost = None            
        second_best_cost = None
        best_location = None
        for route_idx, route in enumerate(routes):
            pos, extra = best_insertion_in_route(inst, dist, route, task)
            if pos is None:
                continue
            if best_cost is None or extra < best_cost:
                second_best_cost = best_cost
                best_cost = extra
                best_location = (route_idx, pos)
            elif second_best_cost is None or extra < second_best_cost:
                second_best_cost = extra
        if best_cost is not None:
            best_r, best_p = best_location
            best_insertion_per_task[task] = (best_r, best_p, best_cost)
        if second_best_cost is not None:
            second_best_insertion_per_task[task] = second_best_cost  
    return best_insertion_per_task, second_best_insertion_per_task

def select_task(best_dict, second_dict, unrouted):
    # Compute regrets and choose task with highest regret
    task_regrets = []
    for task in unrouted:
        best_cost = best_dict[task][2]
        if task in second_dict and second_dict[task] is not None:
            second_best_cost = second_dict[task]
            regret = second_best_cost - best_cost
        else:
            regret = float('inf')
        task_regrets.append((regret, task))
    chosen_task = max(task_regrets)[1]
    return chosen_task

def build_routes_parallel_regret(inst, delivery_day, dist):
    day_tasks = build_day_tasks(inst, delivery_day)
    day_routes = {}

    for day in sorted(day_tasks):
        day_routes[day] = build_routes_parallel(inst, dist, day_tasks[day])
        
    return day_routes
