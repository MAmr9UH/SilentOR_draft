import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("logichain_distribution_model")

    # Decision variables
    y = {}
    for center in data["centers"]:
        y[center] = model.addVar(name=f"y_{center}", vtype=GRB.BINARY)

    f = {}
    for center in data["centers"]:
        for store in data["stores"]:
            f[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)

    # Objective function: Minimize total cost (opening cost + transportation cost)
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

    return model, {"y": y, "f": f}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "y_c1": variables["y"]["c1"].x,
            "y_c2": variables["y"]["c2"].x,
            "y_c3": variables["y"]["c3"].x,
            "y_c4": variables["y"]["c4"].x,
            "f_c1_s1": variables["f"]["c1", "s1"].x,
            "f_c1_s2": variables["f"]["c1", "s2"].x,
            "f_c1_s3": variables["f"]["c1", "s3"].x,
            "f_c1_s4": variables["f"]["c1", "s4"].x,
            "f_c1_s5": variables["f"]["c1", "s5"].x,
            "f_c1_s6": variables["f"]["c1", "s6"].x,
            "f_c1_s7": variables["f"]["c1", "s7"].x,
            "f_c1_s8": variables["f"]["c1", "s8"].x,
            "f_c2_s1": variables["f"]["c2", "s1"].x,
            "f_c2_s2": variables["f"]["c2", "s2"].x,
            "f_c2_s3": variables["f"]["c2", "s3"].x,
            "f_c2_s4": variables["f"]["c2", "s4"].x,
            "f_c2_s5": variables["f"]["c2", "s5"].x,
            "f_c2_s6": variables["f"]["c2", "s6"].x,
            "f_c2_s7": variables["f"]["c2", "s7"].x,
            "f_c2_s8": variables["f"]["c2", "s8"].x,
            "f_c3_s1": variables["f"]["c3", "s1"].x,
            "f_c3_s2": variables["f"]["c3", "s2"].x,
            "f_c3_s3": variables["f"]["c3", "s3"].x,
            "f_c3_s4": variables["f"]["c3", "s4"].x,
            "f_c3_s5": variables["f"]["c3", "s5"].x,
            "f_c3_s6": variables["f"]["c3", "s6"].x,
            "f_c3_s7": variables["f"]["c3", "s7"].x,
            "f_c3_s8": variables["f"]["c3", "s8"].x,
            "f_c4_s1": variables["f"]["c4", "s1"].x,
            "f_c4_s2": variables["f"]["c4", "s2"].x,
            "f_c4_s3": variables["f"]["c4", "s3"].x,
            "f_c4_s4": variables["f"]["c4", "s4"].x,
            "f_c4_s5": variables["f"]["c4", "s5"].x,
            "f_c4_s6": variables["f"]["c4", "s6"].x,
            "f_c4_s7": variables["f"]["c4", "s7"].x,
            "f_c4_s8": variables["f"]["c4", "s8"].x
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