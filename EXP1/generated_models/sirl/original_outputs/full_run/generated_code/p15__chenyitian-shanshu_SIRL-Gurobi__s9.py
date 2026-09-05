import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("distribution_center_model")
    
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
        model.addConstr(gp.quicksum(data["transport_cost"][center][store] * f[center, store] for store in data["stores"]) <= data["capacity"][center])

    return model, {"y": y, "f": f}

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
            "f_c1_s1": variables["f"]["c1", "s1"],
            "f_c1_s2": variables["f"]["c1", "s2"],
            "f_c1_s3": variables["f"]["c1", "s3"],
            "f_c1_s4": variables["f"]["c1", "s4"],
            "f_c1_s5": variables["f"]["c1", "s5"],
            "f_c1_s6": variables["f"]["c1", "s6"],
            "f_c1_s7": variables["f"]["c1", "s7"],
            "f_c2_s1": variables["f"]["c2", "s1"],
            "f_c2_s2": variables["f"]["c2", "s2"],
            "f_c2_s3": variables["f"]["c2", "s3"],
            "f_c2_s4": variables["f"]["c2", "s4"],
            "f_c2_s5": variables["f"]["c2", "s5"],
            "f_c2_s6": variables["f"]["c2", "s6"],
            "f_c2_s7": variables["f"]["c2", "s7"],
            "f_c3_s1": variables["f"]["c3", "s1"],
            "f_c3_s2": variables["f"]["c3", "s2"],
            "f_c3_s3": variables["f"]["c3", "s3"],
            "f_c3_s4": variables["f"]["c3", "s4"],
            "f_c3_s5": variables["f"]["c3", "s5"],
            "f_c3_s6": variables["f"]["c3", "s6"],
            "f_c3_s7": variables["f"]["c3", "s7"],
            "f_c4_s1": variables["f"]["c4", "s1"],
            "f_c4_s2": variables["f"]["c4", "s2"],
            "f_c4_s3": variables["f"]["c4", "s3"],
            "f_c4_s4": variables["f"]["c4", "s4"],
            "f_c4_s5": variables["f"]["c4", "s5"],
            "f_c4_s6": variables["f"]["c4", "s6"],
            "f_c4_s7": variables["f"]["c4", "s7"],
            "f_c5_s1": variables["f"]["c5", "s1"],
            "f_c5_s2": variables["f"]["c5", "s2"],
            "f_c5_s3": variables["f"]["c5", "s3"],
            "f_c5_s4": variables["f"]["c5", "s4"],
            "f_c5_s5": variables["f"]["c5", "s5"],
            "f_c5_s6": variables["f"]["c5", "s6"],
            "f_c5_s7": variables["f"]["c5", "s7"]
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

# Given data
data = {
    "centers": ["c1", "c2", "c3", "c4", "c5"],
    "stores": ["s1", "s2", "s3", "s4", "s5", "s6", "s7"],
    "fixed_opening_cost": {
        "c1": 151000,
        "c2": 192000,
        "c3": 114000,
        "c4": 171000,
        "c5": 160000
    },
    "transport_cost": {
        "c1": {
            "s1": 5,
            "s2": 2,
            "s3": 3,
            "s4": 3,
            "s5": 3,
            "s6": 5,
            "s7": 4
        },
        "c2": {
            "s1": 3,
            "s2": 5,
            "s3": 2,
            "s4": 4,
            "s5": 2,
            "s6": 4,
            "s7": 5
        },
        "c3": {
            "s1": 1,
            "s2": 4,
            "s3": 2,
            "s4": 5,
            "s5": 4,
            "s6": 1,
            "s7": 1
        },
        "c4": {
            "s1": 3,
            "s2": 3,
            "s3": 2,
            "s4": 4,
            "s5": 4,
            "s6": 3,
            "s7": 4
        },
        "c5": {
            "s1": 4,
            "s2": 1,
            "s3": 3,
            "s4": 5,
            "s5": 3,
            "s6": 5,
            "s7": 1
        }
    },
    "demand": {
        "s1": 566,
        "s2": 673,
        "s3": 787,
        "s4": 1000,
        "s5": 715,
        "s6": 413,
        "s7": 641
    },
    "capacity": {
        "c1": 1576,
        "c2": 1364,
        "c3": 1697,
        "c4": 891,
        "c5": 1755
    }
}

solution = solve(data)
print(solution)