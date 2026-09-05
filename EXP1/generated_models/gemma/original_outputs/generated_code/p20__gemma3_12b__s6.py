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
        "variables_keys": [
            f"y_{c}" for c in data["centers"]
        ] + [
            f"f_{c}_{s}" for c in data["centers"] for s in data["stores"]
        ],
        "note": "Scalar variables under EXACTLY these flat keys. The returned solution uses the same keys."
    }

    # Objective function
    model.setObjective(
        gp.quicksum(data["fixed_opening_cost"][c] * y[c] for c in data["centers"]) +
        gp.quicksum(data["transport_cost"][c][s] * f[c, s] for c in data["centers"] for s in data["stores"]),
        GRB.MINIMIZE
    )

    # Constraints
    for s in data["stores"]:
        model.addConstr(
            gp.quicksum(f[c, s] for c in data["centers"]) >= data["demand"][s], name=f"demand_{s}"
        )

    for c in data["centers"]:
        model.addConstr(
            gp.quicksum(f[c, s] for s in data["stores"]) <= data["capacity"][c], name=f"capacity_{c}"
        )

    for c in data["centers"]:
        model.addConstr(
            f[c, "s1"] <= data["capacity"][c] * y[c] if "s1" in data["stores"] else None
        )
        model.addConstr(
            f[c, "s2"] <= data["capacity"][c] * y[c] if "s2" in data["stores"] else None
        )
        model.addConstr(
            f[c, "s3"] <= data["capacity"][c] * y[c] if "s3" in data["stores"] else None
        )
        model.addConstr(
            f[c, "s4"] <= data["capacity"][c] * y[c] if "s4" in data["stores"] else None
        )
        model.addConstr(
            f[c, "s5"] <= data["capacity"][c] * y[c] if "s5" in data["stores"] else None
        )

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
        "y_c6": float(model.getVarByName("y_c6").X),
        "y_c7": float(model.getVarByName("y_c7").X),
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
        "f_c5_s5": float(model.getVarByName("f_c5_s5").X),
        "f_c6_s1": float(model.getVarByName("f_c6_s1").X),
        "f_c6_s2": float(model.getVarByName("f_c6_s2").X),
        "f_c6_s3": float(model.getVarByName("f_c6_s3").X),
        "f_c6_s4": float(model.getVarByName("f_c6_s4").X),
        "f_c6_s5": float(model.getVarByName("f_c6_s5").X),
        "f_c7_s1": float(model.getVarByName("f_c7_s1").X),
        "f_c7_s2": float(model.getVarByName("f_c7_s2").X),
        "f_c7_s3": float(model.getVarByName("f_c7_s3").X),
        "f_c7_s4": float(model.getVarByName("f_c7_s4").X),
        "f_c7_s5": float(model.getVarByName("f_c7_s5").X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }