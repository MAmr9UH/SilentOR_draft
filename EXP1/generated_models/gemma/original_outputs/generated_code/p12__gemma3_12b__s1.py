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
        "variables_keys": {
            "y_c1": "binary Var: 1 if distribution center is opened",
            "y_c2": "binary Var: 1 if distribution center is opened",
            "y_c3": "binary Var: 1 if distribution center is opened",
            "y_c4": "binary Var: 1 if distribution center is opened",
            "y_c5": "binary Var: 1 if distribution center is opened",
            "f_c1_s1": "continuous Var: units shipped from center to store",
            "f_c1_s2": "continuous Var: units shipped from center to store",
            "f_c1_s3": "continuous Var: units shipped from center to store",
            "f_c1_s4": "continuous Var: units shipped from center to store",
            "f_c1_s5": "continuous Var: units shipped from center to store",
            "f_c2_s1": "continuous Var: units shipped from center to store",
            "f_c2_s2": "continuous Var: units shipped from center to store",
            "f_c2_s3": "continuous Var: units shipped from center to store",
            "f_c2_s4": "continuous Var: units shipped from center to store",
            "f_c2_s5": "continuous Var: units shipped from center to store",
            "f_c3_s1": "continuous Var: units shipped from center to store",
            "f_c3_s2": "continuous Var: units shipped from center to store",
            "f_c3_s3": "continuous Var: units shipped from center to store",
            "f_c3_s4": "continuous Var: units shipped from center to store",
            "f_c3_s5": "continuous Var: units shipped from center to store",
            "f_c4_s1": "continuous Var: units shipped from center to store",
            "f_c4_s2": "continuous Var: units shipped from center to store",
            "f_c4_s3": "continuous Var: units shipped from center to store",
            "f_c4_s4": "continuous Var: units shipped from center to store",
            "f_c4_s5": "continuous Var: units shipped from center to store",
            "f_c5_s1": "continuous Var: units shipped from center to store",
            "f_c5_s2": "continuous Var: units shipped from center to store",
            "f_c5_s3": "continuous Var: units shipped from center to store",
            "f_c5_s4": "continuous Var: units shipped from center to store",
            "f_c5_s5": "continuous Var: units shipped from center to store"
        },
        "note": "Scalar variables under EXACTLY these flat keys. The returned solution uses the same keys."
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
        "y_c1": float(model.getVarByName("y_c1").X),
        "y_c2": float(model.getVarByName("y_c2").X),
        "y_c3": float(model.getVarByName("y_c3").X),
        "y_c4": float(model.getVarByName("y_c4").X),
        "y_c5": float(model.getVarByName("y_c5").X),
        "f_c1_s1": float(model.getVarByName("f_c1_s1").X),
        "f_c1_s2": float(model.getVarByName("f_c1_s2").X),
        "f_c1_s3": float(model.getVarByName("f_c1_s3").X),
        "f_c1_s4": float(model.getVarByName("f_c1_s4").X),
        "f_c1_s5": float(model.getVarByName("f_c1_s5").X),
        "f_c2_s1": float(model.getVarByName("f_c2_s1").X),
        "f_c2_s2": float(model.getVarByName("f_c2_s2").X),
        "f_c2_s3": float(model.getVarByName("f_c2_s3").X),
        "f_c2_s4": float(model.getVarByName("f_c2_s4").X),
        "f_c2_s5": float(model.getVarByName("f_c2_s5").X),
        "f_c3_s1": float(model.getVarByName("f_c3_s1").X),
        "f_c3_s2": float(model.getVarByName("f_c3_s2").X),
        "f_c3_s3": float(model.getVarByName("f_c3_s3").X),
        "f_c3_s4": float(model.getVarByName("f_c3_s4").X),
        "f_c3_s5": float(model.getVarByName("f_c3_s5").X),
        "f_c4_s1": float(model.getVarByName("f_c4_s1").X),
        "f_c4_s2": float(model.getVarByName("f_c4_s2").X),
        "f_c4_s3": float(model.getVarByName("f_c4_s3").X),
        "f_c4_s4": float(model.getVarByName("f_c4_s4").X),
        "f_c4_s5": float(model.getVarByName("f_c4_s5").X),
        "f_c5_s1": float(model.getVarByName("f_c5_s1").X),
        "f_c5_s2": float(model.getVarByName("f_c5_s2").X),
        "f_c5_s3": float(model.getVarByName("f_c5_s3").X),
        "f_c5_s4": float(model.getVarByName("f_c5_s4").X),
        "f_c5_s5": float(model.getVarByName("f_c5_s5").X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }