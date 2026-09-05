import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables
    y = {}
    for c in data["centers"]:
        y[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in data["centers"]:
        for s in data["stores"]:
            f[c, s] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"f_{c}_{s}")

    variables = {
        "y_c1": y["c1"],
        "y_c2": y["c2"],
        "y_c3": y["c3"],
        "y_c4": y["c4"],
        "y_c5": y["c5"],
        "y_c6": y["c6"],
        "y_c7": y["c7"],
        "f_c1_s1": f["c1", "s1"],
        "f_c1_s2": f["c1", "s2"],
        "f_c1_s3": f["c1", "s3"],
        "f_c1_s4": f["c1", "s4"],
        "f_c2_s1": f["c2", "s1"],
        "f_c2_s2": f["c2", "s2"],
        "f_c2_s3": f["c2", "s3"],
        "f_c2_s4": f["c2", "s4"],
        "f_c3_s1": f["c3", "s1"],
        "f_c3_s2": f["c3", "s2"],
        "f_c3_s3": f["c3", "s3"],
        "f_c3_s4": f["c3", "s4"],
        "f_c4_s1": f["c4", "s1"],
        "f_c4_s2": f["c4", "s2"],
        "f_c4_s3": f["c4", "s3"],
        "f_c4_s4": f["c4", "s4"],
        "f_c5_s1": f["c5", "s1"],
        "f_c5_s2": f["c5", "s2"],
        "f_c5_s3": f["c5", "s3"],
        "f_c5_s4": f["c5", "s4"],
        "f_c6_s1": f["c6", "s1"],
        "f_c6_s2": f["c6", "s2"],
        "f_c6_s3": f["c6", "s3"],
        "f_c6_s4": f["c6", "s4"],
        "f_c7_s1": f["c7", "s1"],
        "f_c7_s2": f["c7", "s2"],
        "f_c7_s3": f["c7", "s3"],
        "f_c7_s4": f["c7", "s4"]
    }

    # Objective function
    objective = gp.quicksum(data["fixed_opening_cost"][c] * y[c] for c in data["centers"]) \
                + gp.quicksum(data["transport_cost"][c][s] * f[c, s] for c in data["centers"] for s in data["stores"])
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints
    for s in data["stores"]:
        model.addConstr(gp.quicksum(f[c, s] for c in data["centers"]) == data["demand"][s], name=f"demand_{s}")

    for c in data["centers"]:
        model.addConstr(gp.quicksum(f[c, s] for s in data["stores"]) <= data["capacity"][c] * y[c], name=f"supply_{c}")

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
        "y_c1": float(y["c1"].X),
        "y_c2": float(y["c2"].X),
        "y_c3": float(y["c3"].X),
        "y_c4": float(y["c4"].X),
        "y_c5": float(y["c5"].X),
        "y_c6": float(y["c6"].X),
        "y_c7": float(y["c7"].X),
        "f_c1_s1": float(f["c1", "s1"].X),
        "f_c1_s2": float(f["c1", "s2"].X),
        "f_c1_s3": float(f["c1", "s3"].X),
        "f_c1_s4": float(f["c1", "s4"].X),
        "f_c2_s1": float(f["c2", "s1"].X),
        "f_c2_s2": float(f["c2", "s2"].X),
        "f_c2_s3": float(f["c2", "s3"].X),
        "f_c2_s4": float(f["c2", "s4"].X),
        "f_c3_s1": float(f["c3", "s1"].X),
        "f_c3_s2": float(f["c3", "s2"].X),
        "f_c3_s3": float(f["c3", "s3"].X),
        "f_c3_s4": float(f["c3", "s4"].X),
        "f_c4_s1": float(f["c4", "s1"].X),
        "f_c4_s2": float(f["c4", "s2"].X),
        "f_c4_s3": float(f["c4", "s3"].X),
        "f_c4_s4": float(f["c4", "s4"].X),
        "f_c5_s1": float(f["c5", "s1"].X),
        "f_c5_s2": float(f["c5", "s2"].X),
        "f_c5_s3": float(f["c5", "s3"].X),
        "f_c5_s4": float(f["c5", "s4"].X),
        "f_c6_s1": float(f["c6", "s1"].X),
        "f_c6_s2": float(f["c6", "s2"].X),
        "f_c6_s3": float(f["c6", "s3"].X),
        "f_c6_s4": float(f["c6", "s4"].X),
        "f_c7_s1": float(f["c7", "s1"].X),
        "f_c7_s2": float(f["c7", "s2"].X),
        "f_c7_s3": float(f["c7", "s3"].X),
        "f_c7_s4": float(f["c7", "s4"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }