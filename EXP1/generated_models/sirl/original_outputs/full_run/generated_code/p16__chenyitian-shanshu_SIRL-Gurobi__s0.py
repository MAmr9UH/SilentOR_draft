import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("supply_distribution_model")

    # Define decision variables
    y = {}
    f = {}

    for center in data["centers"]:
        y[center] = model.addVar(name=f"y_{center}", vtype=GRB.BINARY)

    for center in data["centers"]:
        for store in data["stores"]:
            f[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)

    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(data["fixed_opening_cost"][center] * y[center] for center in data["centers"]) +
        gp.quicksum(data["transport_cost"][center][store] * f[center, store] for center in data["centers"] for store in data["stores"]),
        GRB.MINIMIZE)

    # Demand at each store
    for store in data["stores"]:
        model.addConstr(gp.quicksum(f[center, store] for center in data["centers"]) >= data["demand"][store])

    # Capacity limit for each distribution center
    for center in data["centers"]:
        model.addConstr(gp.quicksum(f[center, store] for store in data["stores"]) <= data["capacity"][center])

    return model, {
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

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "y_c1": variables["y_c1"].x,
                "y_c2": variables["y_c2"].x,
                "y_c3": variables["y_c3"].x,
                "y_c4": variables["y_c4"].x,
                "y_c5": variables["y_c5"].x,
                "y_c6": variables["y_c6"].x,
                "y_c7": variables["y_c7"].x,
                "f_c1_s1": variables["f_c1_s1"].x,
                "f_c1_s2": variables["f_c1_s2"].x,
                "f_c1_s3": variables["f_c1_s3"].x,
                "f_c1_s4": variables["f_c1_s4"].x,
                "f_c2_s1": variables["f_c2_s1"].x,
                "f_c2_s2": variables["f_c2_s2"].x,
                "f_c2_s3": variables["f_c2_s3"].x,
                "f_c2_s4": variables["f_c2_s4"].x,
                "f_c3_s1": variables["f_c3_s1"].x,
                "f_c3_s2": variables["f_c3_s2"].x,
                "f_c3_s3": variables["f_c3_s3"].x,
                "f_c3_s4": variables["f_c3_s4"].x,
                "f_c4_s1": variables["f_c4_s1"].x,
                "f_c4_s2": variables["f_c4_s2"].x,
                "f_c4_s3": variables["f_c4_s3"].x,
                "f_c4_s4": variables["f_c4_s4"].x,
                "f_c5_s1": variables["f_c5_s1"].x,
                "f_c5_s2": variables["f_c5_s2"].x,
                "f_c5_s3": variables["f_c5_s3"].x,
                "f_c5_s4": variables["f_c5_s4"].x,
                "f_c6_s1": variables["f_c6_s1"].x,
                "f_c6_s2": variables["f_c6_s2"].x,
                "f_c6_s3": variables["f_c6_s3"].x,
                "f_c6_s4": variables["f_c6_s4"].x,
                "f_c7_s1": variables["f_c7_s1"].x,
                "f_c7_s2": variables["f_c7_s2"].x,
                "f_c7_s3": variables["f_c7_s3"].x,
                "f_c7_s4": variables["f_c7_s4"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }