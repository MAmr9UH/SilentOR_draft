import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    days = data.get("days", [])
    n = len(days)
    demand = data.get("demand", {})
    # Create model
    model = gp.Model()

    # Decision variables: number of workers whose 5-day stretch starts on each day
    start_vars = {}
    for idx, day in enumerate(days):
        var = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"start_{day}")
        start_vars[day] = var

    model.update()

    # Objective: minimize total number of workers (sum of starts)
    model.setObjective(gp.quicksum(start_vars[day] for day in days), GRB.MINIMIZE)

    # Constraints: for each day, the number working that day must meet demand
    for i, day in enumerate(days):
        # Workers starting on days i, i-1, i-2, i-3, i-4 (mod 7) work on day i
        working_today = gp.quicksum(start_vars[days[(i - k) % n]] for k in range(5))
        model.addConstr(working_today >= demand.get(day, 0), name=f"coverage_{day}")

    # Prepare the expected variables dict with exact keys
    variables = {
        "start_Monday": start_vars["Monday"],
        "start_Tuesday": start_vars["Tuesday"],
        "start_Wednesday": start_vars["Wednesday"],
        "start_Thursday": start_vars["Thursday"],
        "start_Friday": start_vars["Friday"],
        "start_Saturday": start_vars["Saturday"],
        "start_Sunday": start_vars["Sunday"]
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_int, str(status_int))

    obj_val = model.ObjVal
    solution = {
        "start_Monday": int(variables["start_Monday"].X),
        "start_Tuesday": int(variables["start_Tuesday"].X),
        "start_Wednesday": int(variables["start_Wednesday"].X),
        "start_Thursday": int(variables["start_Thursday"].X),
        "start_Friday": int(variables["start_Friday"].X),
        "start_Saturday": int(variables["start_Saturday"].X),
        "start_Sunday": int(variables["start_Sunday"].X)
    }

    return {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": solution
    }