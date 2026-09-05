import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("bandwidth_maximization_model")
    
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_service_node = data["required_service_node"]
    bandwidth = data["bandwidth"]
    
    variables_keys = {
        "z": "continuous Var: bottleneck bandwidth",
        "x_A_B": "binary Var: 1 if this directed arc is selected",
        "x_A_C": "binary Var: 1 if this directed arc is selected",
        "x_A_E": "binary Var: 1 if this directed arc is selected",
        "x_B_A": "binary Var: 1 if this directed arc is selected",
        "x_B_C": "binary Var: 1 if this directed arc is selected",
        "x_B_D": "binary Var: 1 if this directed arc is selected",
        "x_B_E": "binary Var: 1 if this directed arc is selected",
        "x_C_A": "binary Var: 1 if this directed arc is selected",
        "x_C_D": "binary Var: 1 if this directed arc is selected",
        "x_C_E": "binary Var: 1 if this directed arc is selected",
        "x_D_A": "binary Var: 1 if this directed arc is selected",
        "x_D_B": "binary Var: 1 if this directed arc is selected",
        "x_D_C": "binary Var: 1 if this directed arc is selected",
        "x_D_E": "binary Var: 1 if this directed arc is selected",
        "x_E_B": "binary Var: 1 if this directed arc is selected",
        "x_E_D": "binary Var: 1 if this directed arc is selected"
    }
    
    variables = {}
    
    # Define decision variables
    for key in variables_keys:
        if "x" in key:
            variables[key] = model.addVar(name=key, vtype=GRB.BINARY)
        else:
            variables[key] = model.addVar(name=key, lb=0, vtype=GRB.CONTINUOUS)
    
    # Objective function: Maximize bottleneck bandwidth
    model.setObjective(variables["z"], GRB.MAXIMIZE)
    
    # Bandwidth constraints
    for i in nodes:
        for j in nodes:
            if bandwidth[i][j] > 0:
                model.addConstr(variables[f"x_{i}_{j}"] * bandwidth[i][j] >= variables["z"])
    
    # Flow conservation for all nodes except source and sink
    for i in nodes:
        if i != source and i != sink and i != required_service_node:
            model.addConstr(gp.quicksum(variables[f"x_{i}_{j}"] for j in nodes if (j != i and bandwidth[i][j] > 0)) == 
                           gp.quicksum(variables[f"x_{j}_{i}"] for j in nodes if (j != i and bandwidth[j][i] > 0)))
    
    # Flow through required service node
    model.addConstr(gp.quicksum(variables[f"x_{source}_{j}"] for j in nodes if (j != source and bandwidth[source][j] > 0)) == 
                   variables["x_A_C"] + variables["x_A_D"])
    model.addConstr(gp.quicksum(variables[f"x_{j}_{source}"] for j in nodes if (j != source and bandwidth[j][source] > 0)) == 
                   variables["x_C_A"] + variables["x_D_A"])
    
    model.addConstr(gp.quicksum(variables[f"x_{source}_{j}"] for j in nodes if (j != source and bandwidth[source][j] > 0)) == 1)
    model.addConstr(gp.quicksum(variables[f"x_{j}_{source}"] for j in nodes if (j != source and bandwidth[j][source] > 0)) == 1)
    
    model.addConstr(variables["x_A_C"] + variables["x_B_C"] + variables["x_C_A"] == 1)
    model.addConstr(variables["x_A_E"] + variables["x_B_E"] + variables["x_C_E"] + variables["x_D_E"] + variables["x_E_A"] + variables["x_E_D"] == 1)
    
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