import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables: number of workers on each shift
    s1 = model.addVar(vtype=GRB.INTEGER, name="s1")
    s2 = model.addVar(vtype=GRB.INTEGER, name="s2")
    s3 = model.addVar(vtype=GRB.INTEGER, name="s3")
    s4 = model.addVar(vtype=GRB.INTEGER, name="s4")

    # Objective function: minimize total wage cost
    model.setObjective(
        data["shift_wage"]["1"] * s1 + data["shift_wage"]["2"] * s2 +
        data["shift_wage"]["3"] * s3 + data["shift_wage"]["4"] * s4,
        GRB.MINIMIZE)

    # Constraints: meet worker requirements for each time window
    for w in range(len(data["time_windows"])):
        model.addConstr(
            s1 * (w in data["shift_coverage"]["1"]) + \
            s2 * (w in data["shift_coverage"]["2"]) + \
            s3 * (w in data["shift_coverage"]["3"]) + \
            s4 * (w in data["shift_coverage"]["4"]) >= \
            data["workers_required_by_window"][w],
            f"worker_requirement_{w}")

    variables = {
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4
    }

    return model, variables


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
        "s1": float(variables["s1"].X),
        "s2": float(variables["s2"].X),
        "s3": float(variables["s3"].X),
        "s4": float(variables["s4"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }