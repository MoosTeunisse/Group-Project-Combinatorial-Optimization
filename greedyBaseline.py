"""
=============================================================================
VeRoLog 2017  —  Step 2: Greedy Baseline  +  Step 3: Cost Calculator
=============================================================================

FILE STRUCTURE (place all files in the same directory):
    greedyBaseline.py              <-- THIS FILE
    routingSequential.py            <-- for Step 5, ignore for now
    Solver.py                
    baseCVRPTWUI.py         <-- from the zip, DO NOT modify
    InstanceCVRPTWUI.py     <-- from the zip, DO NOT modify
    Validate.py             <-- from the zip, DO NOT modify

USAGE:
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt
    python Solver.py -i instances/testInstance.txt -o solutions/sol.txt --validate
    python Solver.py --batch instances/ solutions/

WHAT DOES THIS FILE DO?

  STEP 2 — Greedy Baseline (a valid solution, however expensive):
    2A. Assign to each request the earliest possible delivery day
        while respecting tool availability.
        If that fails: repair violations iteratively.
    2B. Send a separate truck for each task: depot -> customer -> depot.
        One task per truck = never capacity or distance issues.
    2C. Write the result in the official tab-separated format.

  STEP 3 — Cost Calculation:
    - VEHICLE_COST      × max vehicles on a single day
    - VEHICLE_DAY_COST  × total vehicle-days
    - DISTANCE_COST     × total travel distance
    - tool.cost         × peak daily tool usage per type
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

from InstanceCVRPTWUI import InstanceCVRPTWUI

# =============================================================================
# HELPER FUNCTION: distance matrix
# =============================================================================

def build_dist_matrix(inst):
    """
    Build an n×n distance matrix based on inst.Coordinates.
    Uses floor of Euclidean distance, as required by the problem.
    """
    n    = len(inst.Coordinates)
    dist = [[0] * n for _ in range(n)]
    for i in range(n):
        ci = inst.Coordinates[i]
        for j in range(i + 1, n):
            cj = inst.Coordinates[j]
            d  = int(math.floor(math.sqrt(
                (ci.X - cj.X) ** 2 + (ci.Y - cj.Y) ** 2
            )))
            dist[i][j] = d
            dist[j][i] = d
    return dist

# =============================================================================
# STEP 2A — Assign delivery days + repair
# =============================================================================

def assign_delivery_days(inst):
    """
    STEP 2A — Assign to each request the earliest possible delivery day
    so that tool availability is not exceeded.

    Phase 1 – Greedy assignment:
      - Sort requests by earliest deadline (strictest first)
      - Choose the earliest day in [fromDay, toDay] that is feasible
      - If no day is feasible: choose the day with the lowest peak
        (emergency fallback — may temporarily cause a violation)

    Phase 2 – Repair:
      - If tool violations remain (due to emergency fallbacks),
        iteratively shift offenders to better days until
        all violations are resolved.

    Validator tool usage definition:
      Tools count as 'outside depot' from delivery day through pickup day
      inclusive: range(delivery_day, pickup_day + 1)

    Returns: dict  request ID -> delivery day
    """
    usage = defaultdict(int)   # (day, tool_id) -> occupancy
    delivery_day = {}

    # ── Phase 1: Greedy assignment ───────────────────────────────────
    sorted_requests = sorted(inst.Requests,
                             key=lambda r: (r.toDay, r.toDay - r.fromDay))

    for req in sorted_requests:
        tool_max = inst.Tools[req.tool - 1].amount
        chosen   = None

        for day in range(req.fromDay, req.toDay + 1):
            occupied = range(day, day + req.numDays + 1)   # incl. pickup day
            if all(usage[(d, req.tool)] + req.toolCount <= tool_max
                   for d in occupied):
                chosen = day
                break

        if chosen is None:
            # Emergency fallback: day with lowest peak occupancy
            chosen = min(
                range(req.fromDay, req.toDay + 1),
                key=lambda day: max(
                    usage[(d, req.tool)]
                    for d in range(day, day + req.numDays + 1)
                )
            )

        delivery_day[req.ID] = chosen
        for d in range(chosen, chosen + req.numDays + 1):
            usage[(d, req.tool)] += req.toolCount

    # ── Phase 2: Repair ──────────────────────────────────────────────
    for _ in range(5000):
        # Find all violations
        violations = {
            (d, t): v
            for (d, t), v in usage.items()
            if v > inst.Tools[t - 1].amount
        }
        if not violations:
            break   # done

        # Pick a random violation
        (vday, vtool), _ = random.choice(list(violations.items()))
        tool_max = inst.Tools[vtool - 1].amount

        # Find requests contributing to this violation
        contributors = [
            req for req in inst.Requests
            if req.tool == vtool
            and vday in range(delivery_day[req.ID],
                              delivery_day[req.ID] + req.numDays + 1)
        ]
        if not contributors:
            break

        # Pick a random contributor and try to shift it
        req = random.choice(contributors)
        cur = delivery_day[req.ID]

        # Remove current contribution
        for d in range(cur, cur + req.numDays + 1):
            usage[(d, req.tool)] -= req.toolCount

        # Find a feasible alternative day
        alternatives = list(range(req.fromDay, req.toDay + 1))
        random.shuffle(alternatives)
        chosen = None

        for day in alternatives:
            if all(usage[(d, req.tool)] + req.toolCount <= tool_max
                   for d in range(day, day + req.numDays + 1)):
                chosen = day
                break

        if chosen is None:
            # No perfect day: choose day with lowest peak
            chosen = min(
                alternatives,
                key=lambda day: max(
                    usage[(d, req.tool)]
                    for d in range(day, day + req.numDays + 1)
                )
            )

        delivery_day[req.ID] = chosen
        for d in range(chosen, chosen + req.numDays + 1):
            usage[(d, req.tool)] += req.toolCount

    return delivery_day

# =============================================================================
# STEP 2B — Build routes: one truck per task
# =============================================================================

def build_routes_baseline(inst, delivery_day):
    """
    STEP 2B — Send a separate truck for each task.

    Each truck drives: depot -> customer -> depot
    Route = [0, task, 0]   where 0 = depot

    Positive task (+r) = delivery of request r
    Negative task (-r) = pickup of request r

    This is the simplest solution that always works:
      - Never capacity issues (one task per truck)
      - Never distance issues (every customer is reachable)

    Returns: dict  day -> list of routes
    """
    day_tasks = defaultdict(list)

    for req in inst.Requests:
        deliver = delivery_day[req.ID]
        pickup  = deliver + req.numDays

        day_tasks[deliver].append(+req.ID)   # delivery
        day_tasks[pickup].append(-req.ID)    # pickup

    days_routes = {}
    for day, tasks in sorted(day_tasks.items()):
        routes = []
        for task in tasks:
            route = [0, task, 0]   # depot -> customer -> depot
            routes.append(route)
        days_routes[day] = routes

    return days_routes

# =============================================================================
# STEP 3 — Cost calculation
# =============================================================================

def compute_cost(inst, dist, delivery_day, days_routes):
    """
    STEP 3 — Calculate the total cost of the solution.

    Cost formula (from the problem):
        VEHICLE_COST      x  max vehicles used on a single day
        VEHICLE_DAY_COST  x  total vehicle-days (sum across all days)
        DISTANCE_COST     x  total travel distance
        tool[i].cost      x  peak daily usage of tool type i

    Tool usage (validator definition):
      Tools count as outside-depot from delivery day through pickup day
      inclusive: range(delivery_day, pickup_day + 1)

    Returns:
        (max_vehicles, total_vehicle_days, tool_use_list,
         total_distance, total_cost)
    """
    num_tools = len(inst.Tools)

    # ── 1. Daily tool usage for objective ───────────────────────────
    tool_use = compute_tool_use_exact_validator(inst, days_routes)

    # ── 2. Vehicles and distance ─────────────────────────────────────
    max_vehicles       = 0
    total_vehicle_days = 0
    total_distance     = 0

    for day, routes in days_routes.items():
        max_vehicles        = max(max_vehicles, len(routes))
        total_vehicle_days += len(routes)

        for route in routes:
            for i in range(len(route) - 1):
                stop_a = route[i]
                stop_b = route[i + 1]

                # 0 = depot, otherwise customer location of that request
                node_a = inst.DepotCoordinate if stop_a == 0 \
                         else inst.Requests[abs(stop_a) - 1].node
                node_b = inst.DepotCoordinate if stop_b == 0 \
                         else inst.Requests[abs(stop_b) - 1].node

                total_distance += dist[node_a][node_b]

    # ── 3. Total cost ────────────────────────────────────────────────
    total_cost = (
          max_vehicles       * inst.VehicleCost
        + total_vehicle_days * inst.VehicleDayCost
        + total_distance     * inst.DistanceCost
        + sum(tool_use[i] * inst.Tools[i].cost for i in range(num_tools))
    )

    return max_vehicles, total_vehicle_days, tool_use, total_distance, total_cost

def compute_tool_use_exact_validator(inst, days_routes):
    """
    Exact copy of the validator's tool-use logic
    """
    toolStatus = [0] * len(inst.Tools)
    toolUse = [0] * len(inst.Tools)

    for dayNumber in range(1, inst.Days + 1):
        routes = days_routes.get(dayNumber, [])

        day_calcStartDepot = [0] * len(inst.Tools)
        day_calcFinishDepot = [0] * len(inst.Tools)

        for route in routes:
            currentTools = [0] * len(inst.Tools)
            depotVisits = [[0] * len(inst.Tools)]
            nodeVisits = []
            lastNode = None

            for node in route:
                if node == 0:
                    if lastNode is not None:
                        bringTools = [0] * len(inst.Tools)
                        sumTools = [0] * len(inst.Tools)

                        for tools in nodeVisits:
                            sumTools = [max(x) for x in zip(tools, sumTools)]
                            bringTools = [min(x) for x in zip(bringTools, tools)]
                            sumTools = [max(0, a) for a in sumTools]

                        depotVisits[-1] = [sum(x) for x in zip(bringTools, depotVisits[-1])]
                        depotVisits.append([b - a for a, b in zip(bringTools, nodeVisits[-1])])

                        currentTools = [0] * len(inst.Tools)
                        nodeVisits = []

                elif node > 0:
                    req = inst.Requests[node - 1]
                    currentTools[req.tool - 1] -= req.toolCount

                elif node < 0:
                    node = -node
                    req = inst.Requests[node - 1]
                    currentTools[req.tool - 1] += req.toolCount

                nodeVisits.append(copy.copy(currentTools))
                lastNode = node

            visitTotal = [0] * len(inst.Tools)
            totalUsedAtStart = [0] * len(inst.Tools)

            for visit in depotVisits:
                visitTotal = [sum(x) for x in zip(visit, visitTotal)]
                totalUsedAtStart = [b - min(0, a) for a, b in zip(visitTotal, totalUsedAtStart)]
                visitTotal = [max(0, a) for a in visitTotal]

            day_calcStartDepot = [b - a for a, b in zip(totalUsedAtStart, day_calcStartDepot)]
            day_calcFinishDepot = [b + a for a, b in zip(visitTotal, day_calcFinishDepot)]

        toolStatus = [sum(x) for x in zip(toolStatus, day_calcStartDepot)]
        toolUse = [max(-a, b) for a, b in zip(toolStatus, toolUse)]
        toolStatus = [sum(x) for x in zip(toolStatus, day_calcFinishDepot)]

    return toolUse

# =============================================================================
# STEP 2C — Write solution
# =============================================================================

def write_solution(inst, dist, delivery_day, days_routes, output_path):
    """
    STEP 2C — Write the solution in the official tab-separated format.

    Each route is written as:
        vehicle_nr  R  0  task  0
    (values separated by tabs)

    Returns the total cost.
    """
    max_v, vdays, tool_use, distance, cost = compute_cost(
        inst, dist, delivery_day, days_routes)

    lines = [
        f"DATASET = {inst.Dataset}",
        f"NAME = {inst.Name}",
        "",
        f"MAX_NUMBER_OF_VEHICLES = {max_v}",
        f"NUMBER_OF_VEHICLE_DAYS = {vdays}",
        f"TOOL_USE = {' '.join(str(t) for t in tool_use)}",
        f"DISTANCE = {distance}",
        f"COST = {cost}",
        "",
    ]

    for day in sorted(days_routes):
        routes = days_routes[day]
        if not routes:
            continue
        lines.append(f"DAY = {day}")
        lines.append(f"NUMBER_OF_VEHICLES = {len(routes)}")
        for vi, route in enumerate(routes):
            lines.append(f"{vi + 1}\tR\t" + "\t".join(str(x) for x in route))
        lines.append("")

    output_dir = os.path.dirname(output_path)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(output_path, 'w') as f:
        f.write("\n".join(lines))

    return cost