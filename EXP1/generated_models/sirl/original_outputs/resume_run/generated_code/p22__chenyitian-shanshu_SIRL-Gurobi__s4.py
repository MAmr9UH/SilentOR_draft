import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("max_bottleneck_bandwidth_model")
    
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_service_node = data["required_service_node"]
    bandwidth = data["bandwidth"]
    big_m = data["big_m"]

    # Initialize decision variables
    variables = {
        "z": model.addVar(name="z", vtype=GRB.CONTINUOUS, lb=0),  # bottleneck bandwidth
        "x_A_B": model.addVar(name="x_A_B", vtype=GRB.BINARY),
        "x_A_C": model.addVar(name="x_A_C", vtype=GRB.BINARY),
        "x_A_E": model.addVar(name="x_A_E", vtype=GRB.BINARY),
        "x_B_A": model.addVar(name="x_B_A", vtype=GRB.BINARY),
        "x_B_C": model.addVar(name="x_B_C", vtype=GRB.BINARY),
        "x_B_D": model.addVar(name="x_B_D", vtype=GRB.BINARY),
        "x_B_E": model.addVar(name="x_B_E", vtype=GRB.BINARY),
        "x_C_A": model.addVar(name="x_C_A", vtype=GRB.BINARY),
        "x_C_D": model.addVar(name="x_C_D", vtype=GRB.BINARY),
        "x_C_E": model.addVar(name="x_C_E", vtype=GRB.BINARY),
        "x_D_A": model.addVar(name="x_D_A", vtype=GRB.BINARY),
        "x_D_B": model.addVar(name="x_D_B", vtype=GRB.BINARY),
        "x_D_C": model.addVar(name="x_D_C", vtype=GRB.BINARY),
        "x_D_E": model.addVar(name="x_D_E", vtype=GRB.BINARY),
        "x_E_B": model.addVar(name="x_E_B", vtype=GRB.BINARY),
        "x_E_D": model.addVar(name="x_E_D", vtype=GRB.BINARY)
    }

    # Objective function: Maximize bottleneck bandwidth
    model.setObjective(variables["z"], GRB.MAXIMIZE)

    # Define bandwidth values
    for node_from in nodes:
        for node_to in nodes:
            if node_from != node_to and bandwidth[node_from][node_to] > 0:
                model.addConstr(variables[f"x_{node_from}_{node_to}"] <= 1)
                model.addConstr(variables[f"x_{node_from}_{node_to}"] * bandwidth[node_from][node_to] >= variables["z"])

    # Ensure the path goes through node C
    model.addConstr(variables["x_A_C"] + variables["x_A_E"] <= 1)
    model.addConstr(variables["x_B_C"] + variables["x_B_E"] <= 1)
    model.addConstr(variables["x_C_A"] + variables["x_C_D"] + variables["x_C_E"] <= 2)
    model.addConstr(variables["x_D_C"] + variables["x_D_A"] + variables["x_D_E"] <= 2)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "z": variables["z"].x,
                "x_A_B": variables["x_A_B"].x,
                "x_A_C": variables["x_A_C"].x,
                "x_A_E": variables["x_A_E"].x,
                "x_B_A": variables["x_B_A"].x,
                "x_B_C": variables["x_B_C"].x,
                "x_B_D": variables["x_B_D"].x,
                "x_B_E": variables["x_B_E"].x,
                "x_C_A": variables["x_C_A"].x,
                "x_C_D": variables["x_C_D"].x,
                "x_C_E": variables["x_C_E"].x,
                "x_D_A": variables["x_D_A"].x,
                "x_D_B": variables["x_D_B"].x,
                "x_D_C": variables["x_D_C"].x,
                "x_D_E": variables["x_D_E"].x,
                "x_E_B": variables["x_E_B"].x,
                "x_E_D": variables["x_E_D"].x
            }
        }
    else:
        solution = {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "z": None,
                "x_A_B": None,
                "x_A_C": None,
                "x_A_E": None,
                "x_B_A": None,
                "x_B_C": None,
                "x_B_D": None,
                "x_B_E": None,
                "x_C_A": None,
                "x_C_D": None,
                "x_C_E": None,
                "x_D_A": None,
                "x_D_B": None,
                "x_D_C": None,
                "x_D_E": None,
                "x_E_B": None,
                "x_E_D": None
            }
        }

    return solution