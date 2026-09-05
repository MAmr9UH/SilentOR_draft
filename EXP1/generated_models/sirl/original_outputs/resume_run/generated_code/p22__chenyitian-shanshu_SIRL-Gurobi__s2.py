import gurobipy as gp
from gurobipy import GRB
import json

def build_model(data: dict) -> tuple:
    model = gp.Model("bandwidth_maximization_model")
    
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_service_node = data["required_service_node"]
    bandwidth = data["bandwidth"]
    
    variables_keys = {
        "z": "bottleneck_bandwidth",
        "x_A_B": "directed_arc_A_B",
        "x_A_C": "directed_arc_A_C",
        "x_A_E": "directed_arc_A_E",
        "x_B_A": "directed_arc_B_A",
        "x_B_C": "directed_arc_B_C",
        "x_B_D": "directed_arc_B_D",
        "x_B_E": "directed_arc_B_E",
        "x_C_A": "directed_arc_C_A",
        "x_C_D": "directed_arc_C_D",
        "x_C_E": "directed_arc_C_E",
        "x_D_A": "directed_arc_D_A",
        "x_D_B": "directed_arc_D_B",
        "x_D_C": "directed_arc_D_C",
        "x_D_E": "directed_arc_D_E",
        "x_E_B": "directed_arc_E_B",
        "x_E_D": "directed_arc_E_D"
    }
    
    variables = {}
    
    # Decision variable for bottleneck bandwidth
    variables["z"] = model.addVar(name="z", vtype=GRB.CONTINUOUS, lb=0)
    
    # Decision variable for each directed arc
    for from_node in nodes:
        for to_node in nodes:
            if bandwidth.get(from_node, {}).get(to_node, 0) > 0:
                variables[f"x_{from_node}_{to_node}"] = model.addVar(name=f"x_{from_node}_{to_node}", vtype=GRB.BINARY)
    
    # Objective function: Maximize the bottleneck bandwidth
    model.setObjective(variables["z"], GRB.MAXIMIZE)
    
    # Constraint: The bandwidth of the link from A to E must pass through C
    model.addConstr(variables["z"] <= variables["x_A_C"])
    model.addConstr(variables["z"] <= variables["x_C_E"])
    
    # Define the bandwidth for each arc
    for from_node in nodes:
        for to_node in nodes:
            if bandwidth.get(from_node, {}).get(to_node, 0) > 0:
                model.addConstr(variables[f"x_{from_node}_{to_node}"] * bandwidth[from_node][to_node] <= variables["z"])
    
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