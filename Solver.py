"""
=============================================================================
VeRoLog 2017 
=============================================================================

FILE STRUCTURE (place all files in the same directory):
    Solver.py              <-- THIS FILE
    baseCVRPTWUI.py         <-- from the zip, DO NOT modify
    InstanceCVRPTWUI.py     <-- from the zip, DO NOT modify
    Validate.py             <-- from the zip, DO NOT modify

USAGE:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
    python Solver.py --batch instances/ solutions/

WHAT DOES THIS FILE DO?
    This is the main solver file.
    It reads an instance, computes a solution using a method, writes
    the solution to a file, and optionally validates it.
=============================================================================
"""

import math
import os
import sys
import argparse
import subprocess
import random
import copy
from collections import defaultdict

from urllib import request
from InstanceCVRPTWUI import InstanceCVRPTWUI

from greedyBaseline import (
    build_dist_matrix,
    assign_delivery_days,
    build_routes_baseline,
    compute_cost,
    write_solution
)

from routingSequential import (
    build_day_tasks,
    route_distance,
    required_initial_load,
    route_load_feasible,
    is_route_feasible,
    best_insertion_in_route,
    pivot_score,
    choose_pivot,
    build_routes_sequential_ex_day,
    build_routes_sequential_ex
)

from routingParallel import (
    build_routes_parallel_regret
)

# =============================================================================
# MAIN FUNCTION
# =============================================================================

def solve(instance_path, output_path, verbose=True):
    """Run Step 2 and Step 3 for a single instance."""
    inst = InstanceCVRPTWUI(instance_path)
    if not inst.isValid():
        print(f"ERROR: invalid instance {instance_path}")
        for error in inst.errorReport:
            print(f"  {error}")


def choose_best_day(instance, request, in_use, day_load, dist):
    tool = instance.Tools[request.tool - 1]
    tool_id = tool.ID


    best_day = None
    best_score = float("inf")

    for delivery_day in range(request.fromDay, request.toDay + 1):
        pickup_day = delivery_day + request.numDays

        feasible = True
        peak_usage = 0

        for day in range(delivery_day, pickup_day):
            new_usage = in_use[tool_id][day] + request.toolCount

            if new_usage > tool.amount:
                feasible = False
                break

            peak_usage = max(peak_usage, new_usage)

        if not feasible:
            continue

       #make sure to tune this to actual relative cost
        current_peak = max(in_use[tool_id])
        new_peak = max(current_peak, peak_usage)

        depot = instance.DepotCoordinate
        distance_penalty = dist[depot][request.node] * 2

        score = (
            tool.cost * (new_peak - current_peak) +               
            2 * (day_load[delivery_day] + day_load[pickup_day]) +
            1 * (delivery_day - request.fromDay) +
            0.5 * distance_penalty
        )

        if score < best_score:
            best_score = score
            best_day = delivery_day

    if best_day is None:
        for delivery_day in range(request.fromDay, request.toDay + 1):
            pickup_day = delivery_day + request.numDays
            feasible = True
            for day in range(delivery_day, pickup_day):
                if in_use[tool_id][day] + request.toolCount > tool.amount:
                    feasible = False
                    break
            if feasible:
                return delivery_day
        raise Exception(f"Could not schedule request {request.ID}")

    return best_day

def compute_total_cost(instance, schedule, in_use, day_load, routes_per_day):
    vehicles_per_day = {
        day: len(routes)
        for day, routes in routes_per_day.items()
    }
    max_vehicles = max(vehicles_per_day.values()) if vehicles_per_day else 0
    vehicle_days = sum(vehicles_per_day.values())

    vehicle_cost_part = instance.VehicleCost * max_vehicles
    vehicle_day_cost_part = instance.VehicleDayCost * vehicle_days

    instance.calculateDistances()
    dist_matrix = instance.calcDistance
    depot = instance.DepotCoordinate
    total_distance = 0

    tool_peak = {}

    for day, routes in routes_per_day.items():
        for route in routes:
            total_distance += route_distance(route, dist_matrix)

    distance_cost_part = instance.DistanceCost * total_distance

    for tool in instance.Tools:
        tool_id = tool.ID
        peak = max(in_use[tool_id]) if in_use[tool_id] else 0
        tool_peak[tool_id] = peak

    tool_cost_part = sum(
        tool.cost * tool_peak[tool.ID]
        for tool in instance.Tools
    )

    total_cost = (
        vehicle_cost_part
        + vehicle_day_cost_part
        + distance_cost_part
        + tool_cost_part
    )

    return total_cost, {
        "vehicle_cost": vehicle_cost_part,
        "vehicle_day_cost": vehicle_day_cost_part,
        "distance_cost": distance_cost_part,
        "tool_cost": tool_cost_part,
        "max_vehicles": max_vehicles,
        "vehicle_days": vehicle_days,
        "total_distance": total_distance,
        "tool_peak": tool_peak,
    }

def main():
    #You can run this file by typing "python Solver.py "instances 2026\instances\B1.txt"" in the command line
    #of course you can use a different file, the above is just an example.
    
    if len(sys.argv) < 2:
        print("Usage: python Solver.py <instance_file>")
        sys.exit(1)
    
    #print("=== NEW VERSION RUNNING ===")
        
    input_path = sys.argv[1]
    
    instance = InstanceCVRPTWUI(input_path, "txt")
    instance.calculateDistances()
    dist = instance.calcDistance
    
    #prints the general info about the instance like the costs and stuff
    print("Instance loaded successfully.")
    print("Dataset:", instance.Dataset)
    print("Name:", instance.Name)
    print("Days:", instance.Days)
    print("Capacity:", instance.Capacity)
    print("Max trip distance:", instance.MaxDistance)
    print("Depot coordinate:", instance.DepotCoordinate)
    print("Vehicle cost:", instance.VehicleCost)
    print("Vehicle day cost:", instance.VehicleDayCost)
    print("Distance cost:", instance.DistanceCost)
    print("Number of tools:", len(instance.Tools))
    print("Number of coordinates:", len(instance.Coordinates))
    print("Number of requests:", len(instance.Requests))

    in_use = {
    tool.ID: [0] * (instance.Days + 1)
    for tool in instance.Tools
    }

    day_load = {day: 0 for day in range(1, instance.Days + 1)}

    schedule = {}
    
    
    #prints all the info about the first tool
    if instance.Tools:
        t = instance.Tools[0]
        print("First tool details:")
        print("  ID:", t.ID)
        print("  Weight:", t.weight)
        print("  Amount:", t.amount)
        print("  Cost:", t.cost)
    
    #prints all the info about the first request
    if instance.Requests:
        r = instance.Requests[0]
        print("First request details:")
        print("  ID:", r.ID)
        print("  Node:", r.node)
        print("  From day:", r.fromDay)
        print("  To day:", r.toDay)
        print("  Number of days:", r.numDays)
        print("  Tool:", r.tool)
        print("  Tool count:", r.toolCount)

    #prints the coordinates of the first request's node
    if instance.Coordinates:
        c = instance.Coordinates[instance.Requests[0].node]
        print("First coordinate details:")
        print("  ID:", c.ID)
        print("  X:", c.X)
        print("  Y:", c.Y)

    depot = instance.DepotCoordinate
    requests_sorted = sorted(
    instance.Requests,
    key=lambda r: ((r.toDay - r.fromDay), -r.toolCount, dist[depot][r.node])
    )

    for request in requests_sorted:
        tool = instance.Tools[request.tool - 1]
        total_weight = tool.weight * request.toolCount

        if total_weight > instance.Capacity:
            raise Exception(f"Request {request.ID} exceeds vehicle capacity and cannot be scheduled.")
        delivery_day = choose_best_day(instance, request, in_use, day_load, dist)
        pickup_day = delivery_day + request.numDays

    
        for day in range(delivery_day, pickup_day):
            tool_id = instance.Tools[request.tool - 1].ID
            in_use[tool_id][day] += request.toolCount
            #print(f"Scheduling request {request.ID}")

    
        day_load[delivery_day] += 1
        day_load[pickup_day] += 1

    
        schedule[request.ID] = (delivery_day, pickup_day)

    print("NUMBER OF SCHEDULED REQUESTS:", len(schedule))

    routes_per_day = {}
    for day in range (1, instance.Days + 1):
        tasks = build_day_tasks(instance, schedule, day)
        if not tasks:
            routes_per_day[day] = []
            continue
        routes = build_routes_parallel_regret(instance, tasks, dist)
        routes_per_day[day] = routes

    total_cost, breakdown = compute_total_cost(
    instance, schedule, in_use, day_load, routes_per_day
    )

    print("\nCOST BREAKDOWN:")
    for k, v in breakdown.items():
        print(f"{k}: {v}")

    print("\nTOTAL COST:", total_cost)

    print("\nSCHEDULE:")
    for req_id, (d, p) in schedule.items():
        print(f"Request {req_id}: deliver day {d}, pickup day {p}")

if __name__ == "__main__":
    main()
    