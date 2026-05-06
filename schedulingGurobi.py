import gurobipy as gp
from gurobipy import GRB

def assign_delivery_days_gurobi(inst, dist, time_limit=60, verbose=False):
    model = gp.Model("delivery_days")
    model.Params.OutputFlag = 1 if verbose else 0
    model.Params.TimeLimit = time_limit

    x = make_delivery_vars(model, inst)
    tool_peak = make_tool_peak_vars(model, inst)

    add_delivery_constraints(model, inst, x)
    add_tool_constraints(model, inst, x, tool_peak)

    objective = make_objective(inst, dist, x, tool_peak)
    model.setObjective(objective, GRB.MINIMIZE)

    model.optimize()

    if model.SolCount == 0:
        raise Exception("Gurobi found no feasible schedule.")

    return get_delivery_days(inst, x)

def feasible_days(inst, r):
    result = []

    for d in range(r.fromDay, r.toDay + 1):
        pickup_day = d + r.numDays
        if pickup_day <= inst.Days:
            result.append(d)

    return result


def make_delivery_vars(model, inst):
    x = {}

    for r in inst.Requests:
        for d in feasible_days(inst, r):
            x[r.ID, d] = model.addVar(vtype=GRB.BINARY, name=f"x_{r.ID}_{d}")

    return x


def make_tool_peak_vars(model, inst):
    tool_peak = {}

    for t in inst.Tools:
        tool_peak[t.ID] = model.addVar(
            vtype=GRB.INTEGER,
            lb=0,
            ub=t.amount,
            name=f"tool_peak_{t.ID}"
        )

    return tool_peak


def add_delivery_constraints(model, inst, x):
    for r in inst.Requests:
        days = feasible_days(inst, r)

        if not days:
            raise Exception(f"Request {r.ID} has no feasible delivery day.")

        model.addConstr(
            gp.quicksum(x[r.ID, d] for d in days) == 1
        )


def add_tool_constraints(model, inst, x, tool_peak):
    for t in inst.Tools:
        for day in range(1, inst.Days + 1):
            usage = gp.quicksum(
                r.toolCount * x[r.ID, d]
                for r in inst.Requests
                if r.tool == t.ID
                for d in feasible_days(inst, r)
                if d <= day <= d + r.numDays - 1
            )

            model.addConstr(usage <= t.amount)
            model.addConstr(tool_peak[t.ID] >= usage)


def make_objective(inst, dist, x, tool_peak):
    depot = inst.DepotCoordinate

    tool_cost = gp.quicksum(
        t.cost * tool_peak[t.ID]
        for t in inst.Tools
    )

    day_load_penalty = gp.quicksum(
        daily_task_count(inst, x, day) * daily_task_count(inst, x, day)
        for day in range(1, inst.Days + 1)
    )
    
    early_penalty = gp.quicksum(
        (d - r.fromDay) * x[r.ID, d]
        for r in inst.Requests
        for d in feasible_days(inst, r)
    )

    distance_penalty = gp.quicksum(
        dist[depot][r.node] * (d - r.fromDay) * x[r.ID, d]
        for r in inst.Requests
        for d in feasible_days(inst, r)
    )

    return (
        tool_cost
        + 10 * day_load_penalty
        + 5 * early_penalty
        + 0.01 * distance_penalty
    )


def daily_task_count(inst, x, day):
    return gp.quicksum(
        x[r.ID, d]
        for r in inst.Requests
        for d in feasible_days(inst, r)
        if d == day or d + r.numDays == day
    )


def get_delivery_days(inst, x):
    delivery_day = {}

    for r in inst.Requests:
        for d in feasible_days(inst, r):
            if x[r.ID, d].X > 0.5:
                delivery_day[r.ID] = d
                break

    print("scheduled", len(delivery_day), "out of", len(inst.Requests))

    return delivery_day