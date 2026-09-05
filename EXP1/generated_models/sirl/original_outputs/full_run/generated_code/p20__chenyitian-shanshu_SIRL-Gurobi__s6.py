import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("supply_chain_model")

    # Initialize decision variables
    y = {}
    f = {}

    # y_c{center}: 1 if distribution center is opened
    for center in data["centers"]:
        y[center] = model.addVar(name=f"y_{center}", vtype=GRB.BINARY)

    # f_c{center}_{store}: units shipped from center to store
    for center in data["centers"]:
        for store in data["stores"]:
            f[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)

    # Objective function: Minimize total cost (opening cost + transportation cost)
    model.setObjective(
        gp.quicksum(data["fixed_opening_cost"][center] * y[center] for center in data["centers"]) +
        gp.quicksum(data["transport_cost"][center][store] * f[center, store] for center in data["centers"] for store in data["stores"]),
        GRB.MINIMIZE)

    # Each store's demand must be met
    for store in data["stores"]:
        model.addConstr(gp.quicksum(f[center, store] for center in data["centers"]) >= data["demand"][store])

    # Capacity of each distribution center
    for center in data["centers"]:
        model.addConstr(gp.quicksum(data["transport_cost"][center][store] * f[center, store] for store in data["stores"]) <= data["capacity"][center] * y[center])

    return model, {"y": y, "f": f}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "y_c1": variables["y"]["c1"].x,
                "y_c2": variables["y"]["c2"].x,
                "y_c3": variables["y"]["c3"].x,
                "y_c4": variables["y"]["c4"].x,
                "y_c5": variables["y"]["c5"].x,
                "y_c6": variables["y"]["c6"].x,
                "y_c7": variables["y"]["c7"].x,
                "f_c1_s1": variables["f"]["c1"]["s1"],
                "f_c1_s2": variables["f"]["c1"]["s2"],
                "f_c1_s3": variables["f"]["c1"]["s3"],
                "f_c1_s4": variables["f"]["c1"]["s4"],
                "f_c1_s5": variables["f"]["c1"]["s5"],
                "f_c2_s1": variables["f"]["c2"]["s1"],
                "f_c2_s2": variables["f"]["c2"]["s2"],
                "f_c2_s3": variables["f"]["c2"]["s3"],
                "f_c2_s4": variables["f"]["c2"]["s4"],
                "f_c2_s5": variables["f"]["c2"]["s5"],
                "f_c3_s1": variables["f"]["c3"]["s1"],
                "f_c3_s2": variables["f"]["c3"]["s2"],
                "f_c3_s3": variables["f"]["c3"]["s3"],
                "f_c3_s4": variables["f"]["c3"]["s4"],
                "f_c3_s5": variables["f"]["c3"]["s5"],
                "f_c4_s1": variables["f"]["c4"]["s1"],
                "f_c4_s2": variables["f"]["c4"]["s2"],
                "f_c4_s3": variables["f"]["c4"]["s3"],
                "f_c4_s4": variables["f"]["c4"]["s4"],
                "f_c4_s5": variables["f"]["c4"]["s5"],
                "f_c5_s1": variables["f"]["c5"]["s1"],
                "f_c5_s2": variables["f"]["c5"]["s2"],
                "f_c5_s3": variables["f"]["c5"]["s3"],
                "f_c5_s4": variables["f"]["c5"]["s4"],
                "f_c5_s5": variables["f"]["c5"]["s5"],
                "f_c6_s1": variables["f"]["c6"]["s1"],
                "f_c6_s2": variables["f"]["c6"]["s2"],
                "f_c6_s3": variables["f"]["c6"]["s3"],
                "f_c6_s4": variables["f"]["c6"]["s4"],
                "f_c6_s5": variables["f"]["c6"]["s5"],
                "f_c7_s1": variables["f"]["c7"]["s1"],
                "f_c7_s2": variables["f"]["c7"]["s2"],
                "f_c7_s3": variables["f"]["c7"]["s3"],
                "f_c7_s4": variables["f"]["c7"]["s4"],
                "f_c7_s5": variables["f"]["c7"]["s5"]
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {}
        }

    return solution