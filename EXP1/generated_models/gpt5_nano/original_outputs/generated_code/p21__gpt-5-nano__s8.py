import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Day order as provided
    days = data["days"]  # list of 7 day names in order: Monday, ..., Sunday

    # Create variables: start_Monday, ..., start_Sunday
    variables = {}
    for day in days:
        key = "start_" + day
        v = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
        variables[key] = v

    # Objective: minimize total number of workers (sum of all starts)
    obj = gp.quicksum(variables["start_" + day] for day in days)
    model.setObjective(obj, GRB.MINIMIZE)

    # Demands per day
    demand = data["demand"]  # dict with keys like "Monday": value

    # Coverage constraints: for each day i, sum of starts on i, i-1, ..., i-4 (mod 7) >= demand on day i
    for i, day in enumerate(days):
        cover_keys = [ "start_" + days[(i - k) % 7] for k in range(5) ]
        constraint_expr = gp.quicksum( variables[key] for key in cover_keys )
        model.addConstr(constraint_expr >= int(demand[day]), name=f"cover_{day}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    # Read solution values (cast to int for exact counts)
    solution = {
        "start_Monday": int(variables["start_Monday"].X),
        "start_Tuesday": int(variables["start_Tuesday"].X),
        "start_Wednesday": int(variables["start_Wednesday"].X),
        "start_Thursday": int(variables["start_Thursday"].X),
        "start_Friday": int(variables["start_Friday"].X),
        "start_Saturday": int(variables["start_Saturday"].X),
        "start_Sunday": int(variables["start_Sunday"].X),
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }
    return result