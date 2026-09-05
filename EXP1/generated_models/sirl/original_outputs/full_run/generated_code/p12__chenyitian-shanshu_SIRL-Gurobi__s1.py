import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("supply_distribution_model")
    
    centers = data["centers"]
    stores = data["stores"]
    fixed_opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]
    
    # Decision variables
    y = {}
    f = {}
    
    for center in centers:
        y[center] = model.addVar(name=f"y_{center}", vtype=GRB.BINARY, lb=0)
        
    for center in centers:
        for store in stores:
            f[center, store] = model.addVar(name=f"f_{center}_{store}", lb=0)
    
    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(fixed_opening_cost[center] * y[center] for center in centers) +
        gp.quicksum(transport_cost[center][store] * f[center, store] for center in centers for store in stores),
        GRB.MINIMIZE)
    
    # Demand constraint
    for store in stores:
        model.addConstr(gp.quicksum(f[center, store] for center in centers) >= demand[store])
    
    # Capacity constraint
    for center in centers:
        model.addConstr(gp.quicksum(f[center, store] for store in stores) <= capacity[center])
    
    return model, {
        "y_c1": y["c1"],
        "y_c2": y["c2"],
        "y_c3": y["c3"],
        "y_c4": y["c4"],
        "y_c5": y["c5"],
        "f_c1_s1": f["c1", "s1"],
        "f_c1_s2": f["c1", "s2"],
        "f_c1_s3": f["c1", "s3"],
        "f_c1_s4": f["c1", "s4"],
        "f_c1_s5": f["c1", "s5"],
        "f_c2_s1": f["c2", "s1"],
        "f_c2_s2": f["c2", "s2"],
        "f_c2_s3": f["c2", "s3"],
        "f_c2_s4": f["c2", "s4"],
        "f_c2_s5": f["c2", "s5"],
        "f_c3_s1": f["c3", "s1"],
        "f_c3_s2": f["c3", "s2"],
        "f_c3_s3": f["c3", "s3"],
        "f_c3_s4": f["c3", "s4"],
        "f_c3_s5": f["c3", "s5"],
        "f_c4_s1": f["c4", "s1"],
        "f_c4_s2": f["c4", "s2"],
        "f_c4_s3": f["c4", "s3"],
        "f_c4_s4": f["c4", "s4"],
        "f_c4_s5": f["c4", "s5"],
        "f_c5_s1": f["c5", "s1"],
        "f_c5_s2": f["c5", "s2"],
        "f_c5_s3": f["c5", "s3"],
        "f_c5_s4": f["c5", "s4"],
        "f_c5_s5": f["c5", "s5"]
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
                "f_c1_s1": variables["f_c1_s1"].x,
                "f_c1_s2": variables["f_c1_s2"].x,
                "f_c1_s3": variables["f_c1_s3"].x,
                "f_c1_s4": variables["f_c1_s4"].x,
                "f_c1_s5": variables["f_c1_s5"].x,
                "f_c2_s1": variables["f_c2_s1"].x,
                "f_c2_s2": variables["f_c2_s2"].x,
                "f_c2_s3": variables["f_c2_s3"].x,
                "f_c2_s4": variables["f_c2_s4"].x,
                "f_c2_s5": variables["f_c2_s5"].x,
                "f_c3_s1": variables["f_c3_s1"].x,
                "f_c3_s2": variables["f_c3_s2"].x,
                "f_c3_s3": variables["f_c3_s3"].x,
                "f_c3_s4": variables["f_c3_s4"].x,
                "f_c3_s5": variables["f_c3_s5"].x,
                "f_c4_s1": variables["f_c4_s1"].x,
                "f_c4_s2": variables["f_c4_s2"].x,
                "f_c4_s3": variables["f_c4_s3"].x,
                "f_c4_s4": variables["f_c4_s4"].x,
                "f_c4_s5": variables["f_c4_s5"].x,
                "f_c5_s1": variables["f_c5_s1"].x,
                "f_c5_s2": variables["f_c5_s2"].x,
                "f_c5_s3": variables["f_c5_s3"].x,
                "f_c5_s4": variables["f_c5_s4"].x,
                "f_c5_s5": variables["f_c5_s5"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }