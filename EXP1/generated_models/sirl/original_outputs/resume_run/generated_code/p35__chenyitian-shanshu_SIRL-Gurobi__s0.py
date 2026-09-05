import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("transshipment_model")

    # Define decision variables
    x = {}
    for i in data["sources"]:
        for k in data["stations"]:
            x[i, k] = model.addVar(name=f"x_{i}_{k}", vtype=GRB.CONTINUOUS, lb=0)

    z = {}
    for k in data["stations"]:
        for j in data["demands"]:
            z[k, j] = model.addVar(name=f"z_{k}_{j}", vtype=GRB.CONTINUOUS, lb=0)

    y = {}
    for k in data["stations"]:
        y[k] = model.addVar(name=f"y_{k}", vtype=GRB.BINARY)

    # Supply
    a = data["supply"]
    # Demand
    b = data["demand"]
    # Station capacity
    q = data["station_capacity"]
    # Fixed cost
    f = data["fixed_cost"]
    # Cost from source to station
    c = data["cost_source_station"]
    # Cost from station to demand
    c_prime = data["cost_station_demand"]

    # Objective function: Minimize total cost
    model.setObjective(
        gp.quicksum(c[f"{i},{k}"] * x[i, k] for i in data["sources"] for k in data["stations"]) +
        gp.quicksum(c_prime[f"{k},{j}"] * z[k, j] for k in data["stations"] for j in data["demands"]) +
        gp.quicksum(f[k] * y[k] for k in data["stations"]),
        GRB.MINIMIZE)

    # Flow balance at sources
    for i in data["sources"]:
        model.addConstr(gp.quicksum(x[i, k] for k in data["stations"]) == a[i])

    # Flow balance at demands
    for j in data["demands"]:
        model.addConstr(gp.quicksum(z[k, j] for k in data["stations"]) == b[j])

    # Capacity constraint at stations
    for k in data["stations"]:
        model.addConstr(gp.quicksum(x[i, k] for i in data["sources"]) <= q[k] * y[k])

    # Linking x and z
    for k in data["stations"]:
        for i in data["sources"]:
            for j in data["demands"]:
                model.addConstr(z[k, j] >= x[i, k] - q[k] * (1 - y[k]))

    # Given values
    a_1 = data["supply"]["1"]
    a_2 = data["supply"]["2"]
    b_1 = data["demand"]["1"]
    b_2 = data["demand"]["2"]

    # Check supply and demand balance
    model.addConstr(a_1 + a_2 >= b_1 + b_2)

    # Define costs
    c_source_station = {
        ("1", "1"): 2,
        ("1", "2"): 3,
        ("2", "1"): 4,
        ("2", "2"): 1
    }

    c_station_demand = {
        ("1", "1"): 3,
        ("1", "2"): 2,
        ("2", "1"): 1,
        ("2", "2"): 4
    }

    fixed_cost = {
        "1": 10,
        "2": 15
    }

    station_capacity = {
        "1": 100,
        "2": 100
    }

    variables = {
        "x_1_1": x["1", "1"],
        "x_1_2": x["1", "2"],
        "x_2_1": x["2", "1"],
        "x_2_2": x["2", "2"],
        "z_1_1": z["1", "1"],
        "z_1_2": z["1", "2"],
        "z_2_1": z["2", "1"],
        "z_2_2": z["2", "2"],
        "y_1": y["1"],
        "y_2": y["2"]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_1": variables["x_1_1"].x,
            "x_1_2": variables["x_1_2"].x,
            "x_2_1": variables["x_2_1"].x,
            "x_2_2": variables["x_2_2"].x,
            "z_1_1": variables["z_1_1"].x,
            "z_1_2": variables["z_1_2"].x,
            "z_2_1": variables["z_2_1"].x,
            "z_2_2": variables["z_2_2"].x,
            "y_1": variables["y_1"].x,
            "y_2": variables["y_2"].x
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