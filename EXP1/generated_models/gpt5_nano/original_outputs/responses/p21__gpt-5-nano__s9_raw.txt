import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    days = data["days"]
    demand = data["demand"]

    total_demand = sum(demand[day] for day in days)

    model = gp.Model()
    model.Params.OutputFlag = 0  # silence solver output

    # Decision variables: number of workers starting on each day
    starts = {}
    for day in days:
        key = f"start_{day}"
        var = model.addVar(vtype=GRB.INTEGER, lb=0, ub=total_demand, name=key)
        starts[key] = var

    model.update()

    # Constraints: on each day, demand must be met by workers starting that day or in the previous 4 days
    for idx, day in enumerate(days):
        covering = quicksum(starts[f"start_{days[(idx - k) % 7]}"] for k in range(5))
        model.addConstr(covering >= demand[day], name=f"cover_{day}")

    # Objective: minimize total number of workers employed
    model.setObjective(quicksum(starts[key] for key in starts), GRB.MINIMIZE)

    return model, starts

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    objective = model.ObjVal
    if objective is None:
        objective = 0.0

    start_keys = [
        "start_Monday",
        "start_Tuesday",
        "start_Wednesday",
        "start_Thursday",
        "start_Friday",
        "start_Saturday",
        "start_Sunday",
    ]
    solution = {}
    for key in start_keys:
        var = variables[key]
        solution[key] = int(var.X)

    return {
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }