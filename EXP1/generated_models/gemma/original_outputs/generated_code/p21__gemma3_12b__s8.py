import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    days = data["days"]
    demand = data["demand"]
    work_consecutive_days = data["work_consecutive_days"]
    off_consecutive_days = data["off_consecutive_days"]

    # Decision variables: number of workers starting on each day
    start_vars = {}
    for day in days:
        start_vars[day] = gp.GRBVar(vtype=GRB.INTEGER, name=f"start_{day}")

    variables = {
        "variables_keys": {
            "start_Monday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Tuesday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Wednesday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Thursday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Friday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Saturday": "integer Var: number of workers whose five-day work stretch starts on this day",
            "start_Sunday": "integer Var: number of workers whose five-day work stretch starts on this day"
        },
        "note": "Scalar variables under EXACTLY these flat keys. An employee starting on a day works that day and the next four consecutive days, then is off for two days."
    }

    # Objective function: minimize total number of workers
    model.setObjective(gp.quicksum(start_vars[day] for day in days), GRB.MINIMIZE)

    # Constraints: staffing requirements for each day
    for day in days:
        demand_index = days.index(day)
        covered_days = []
        for i in range(work_consecutive_days):
            covered_days.append((demand_index + i) % 7)

        model.addConstr(
            gp.quicksum(start_vars[days[d]] for d in covered_days) >= demand[day],
            f"staffing_{day}"
        )

    return model, {"start_vars": start_vars}


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "start_Monday": float(variables["start_vars"]["Monday"].X),
        "start_Tuesday": float(variables["start_vars"]["Tuesday"].X),
        "start_Wednesday": float(variables["start_vars"]["Wednesday"].X),
        "start_Thursday": float(variables["start_vars"]["Thursday"].X),
        "start_Friday": float(variables["start_vars"]["Friday"].X),
        "start_Saturday": float(variables["start_vars"]["Saturday"].X),
        "start_Sunday": float(variables["start_vars"]["Sunday"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }