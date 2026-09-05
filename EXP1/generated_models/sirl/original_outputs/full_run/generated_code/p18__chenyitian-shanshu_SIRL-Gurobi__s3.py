import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("supply_chain_model")

    # Decision variables
    y = {}
    for center in data["centers"]:
        y[center] = model.addVar(name=f"y_{center}", vtype=GRB.BINARY)

    flow = {}
    for center in data["centers"]:
        for store in data["stores"]:
            flow[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)

    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(data["fixed_opening_cost"][center] * y[center] for center in data["centers"]) +
        gp.quicksum(data["transport_cost"][center][store] * flow[center, store] for center in data["centers"] for store in data["stores"]),
        GRB.MINIMIZE)

    # Demand constraint
    for store in data["stores"]:
        model.addConstr(gp.quicksum(flow[center, store] for center in data["centers"]) >= data["demand"][store])

    # Capacity constraint
    for center in data["centers"]:
        model.addConstr(gp.quicksum(data["transport_cost"][center][store] * flow[center, store] for store in data["stores"]) <= data["capacity"][center])

    return model, {"y": y, "flow": flow}

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "y_c1": variables["y"]["c1"],
            "y_c2": variables["y"]["c2"],
            "y_c3": variables["y"]["c3"],
            "y_c4": variables["y"]["c4"],
            "y_c5": variables["y"]["c5"],
            "y_c6": variables["y"]["c6"],
            "f_c1_s1": variables["flow"]["c1", "s1"],
            "f_c1_s2": variables["flow"]["c1", "s2"],
            "f_c1_s3": variables["flow"]["c1", "s3"],
            "f_c1_s4": variables["flow"]["c1", "s4"],
            "f_c1_s5": variables["flow"]["c1", "s5"],
            "f_c1_s6": variables["flow"]["c1", "s6"],
            "f_c1_s7": variables["flow"]["c1", "s7"],
            "f_c2_s1": variables["flow"]["c2", "s1"],
            "f_c2_s2": variables["flow"]["c2", "s2"],
            "f_c2_s3": variables["flow"]["c2", "s3"],
            "f_c2_s4": variables["flow"]["c2", "s4"],
            "f_c2_s5": variables["flow"]["c2", "s5"],
            "f_c2_s6": variables["flow"]["c2", "s6"],
            "f_c2_s7": variables["flow"]["c2", "s7"],
            "f_c3_s1": variables["flow"]["c3", "s1"],
            "f_c3_s2": variables["flow"]["c3", "s2"],
            "f_c3_s3": variables["flow"]["c3", "s3"],
            "f_c3_s4": variables["flow"]["c3", "s4"],
            "f_c3_s5": variables["flow"]["c3", "s5"],
            "f_c3_s6": variables["flow"]["c3", "s6"],
            "f_c3_s7": variables["flow"]["c3", "s7"],
            "f_c4_s1": variables["flow"]["c4", "s1"],
            "f_c4_s2": variables["flow"]["c4", "s2"],
            "f_c4_s3": variables["flow"]["c4", "s3"],
            "f_c4_s4": variables["flow"]["c4", "s4"],
            "f_c4_s5": variables["flow"]["c4", "s5"],
            "f_c4_s6": variables["flow"]["c4", "s6"],
            "f_c4_s7": variables["flow"]["c4", "s7"],
            "f_c5_s1": variables["flow"]["c5", "s1"],
            "f_c5_s2": variables["flow"]["c5", "s2"],
            "f_c5_s3": variables["flow"]["c5", "s3"],
            "f_c5_s4": variables["flow"]["c5", "s4"],
            "f_c5_s5": variables["flow"]["c5", "s5"],
            "f_c5_s6": variables["flow"]["c5", "s6"],
            "f_c5_s7": variables["flow"]["c5", "s7"],
            "f_c6_s1": variables["flow"]["c6", "s1"],
            "f_c6_s2": variables["flow"]["c6", "s2"],
            "f_c6_s3": variables["flow"]["c6", "s3"],
            "f_c6_s4": variables["flow"]["c6", "s4"],
            "f_c6_s5": variables["flow"]["c6", "s5"],
            "f_c6_s6": variables["flow"]["c6", "s6"],
            "f_c6_s7": variables["flow"]["c6", "s7"]
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