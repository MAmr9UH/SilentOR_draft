import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("logichain_distribution_model")

    # Decision variables
    y = {
        "c1": model.addVar(name="y_c1", vtype=GRB.BINARY),
        "c2": model.addVar(name="y_c2", vtype=GRB.BINARY),
        "c3": model.addVar(name="y_c3", vtype=GRB.BINARY),
        "c4": model.addVar(name="y_c4", vtype=GRB.BINARY)
    }

    f = {}
    for center in data["centers"]:
        for store in data["stores"]:
            f[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)

    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(data["fixed_opening_cost"][center] * y[center] for center in data["centers"]) +
        gp.quicksum(data["transport_cost"][center][store] * f[center, store] for center in data["centers"] for store in data["stores"]),
        GRB.MINIMIZE)

    # Demand constraint
    for store in data["stores"]:
        model.addConstr(gp.quicksum(f[center, store] for center in data["centers"]) >= data["demand"][store])

    # Capacity constraint
    for center in data["centers"]:
        model.addConstr(gp.quicksum(f[center, store] for store in data["stores"]) <= data["capacity"][center])

    return model, {"y_c1": y["c1"], "y_c2": y["c2"], "y_c3": y["c3"], "y_c4": y["c4"], **{f"f_{center}_{store}": f[center, store] for center in data["centers"] for store in data["stores"]}}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "y_c1": variables["y_c1"].x,
            "y_c2": variables["y_c2"].x,
            "y_c3": variables["y_c3"].x,
            "y_c4": variables["y_c4"].x,
            "f_c1_s1": variables["f_c1_s1"].x,
            "f_c1_s2": variables["f_c1_s2"].x,
            "f_c1_s3": variables["f_c1_s3"].x,
            "f_c1_s4": variables["f_c1_s4"].x,
            "f_c1_s5": variables["f_c1_s5"].x,
            "f_c1_s6": variables["f_c1_s6"].x,
            "f_c1_s7": variables["f_c1_s7"].x,
            "f_c1_s8": variables["f_c1_s8"].x,
            "f_c2_s1": variables["f_c2_s1"].x,
            "f_c2_s2": variables["f_c2_s2"].x,
            "f_c2_s3": variables["f_c2_s3"].x,
            "f_c2_s4": variables["f_c2_s4"].x,
            "f_c2_s5": variables["f_c2_s5"].x,
            "f_c2_s6": variables["f_c2_s6"].x,
            "f_c2_s7": variables["f_c2_s7"].x,
            "f_c2_s8": variables["f_c2_s8"].x,
            "f_c3_s1": variables["f_c3_s1"].x,
            "f_c3_s2": variables["f_c3_s2"].x,
            "f_c3_s3": variables["f_c3_s3"].x,
            "f_c3_s4": variables["f_c3_s4"].x,
            "f_c3_s5": variables["f_c3_s5"].x,
            "f_c3_s6": variables["f_c3_s6"].x,
            "f_c3_s7": variables["f_c3_s7"].x,
            "f_c3_s8": variables["f_c3_s8"].x,
            "f_c4_s1": variables["f_c4_s1"].x,
            "f_c4_s2": variables["f_c4_s2"].x,
            "f_c4_s3": variables["f_c4_s3"].x,
            "f_c4_s4": variables["f_c4_s4"].x,
            "f_c4_s5": variables["f_c4_s5"].x,
            "f_c4_s6": variables["f_c4_s6"].x,
            "f_c4_s7": variables["f_c4_s7"].x,
            "f_c4_s8": variables["f_c4_s8"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }