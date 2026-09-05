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
    big_m = data["big_m"]
    
    variables_keys = {
        "z": "bottleneck_bandwidth",
        "x_A_B": "arc_A_B",
        "x_A_C": "arc_A_C",
        "x_A_E": "arc_A_E",
        "x_B_A": "arc_B_A",
        "x_B_C": "arc_B_C",
        "x_B_D": "arc_B_D",
        "x_B_E": "arc_B_E",
        "x_C_A": "arc_C_A",
        "x_C_D": "arc_C_D",
        "x_C_E": "arc_C_E",
        "x_D_A": "arc_D_A",
        "x_D_B": "arc_D_B",
        "x_D_C": "arc_D_C",
        "x_D_E": "arc_D_E",
        "x_E_B": "arc_E_B",
        "x_E_D": "arc_E_D"
    }
    
    # Decision variables
    z = model.addVar(name="z", vtype=GRB.CONTINUOUS, lb=0)
    x = {}
    for (from_node, to_node) in [
        ("A", "B"), ("A", "C"), ("A", "E"),
        ("B", "A"), ("B", "C"), ("B", "D"), ("B", "E"),
        ("C", "A"), ("C", "D"), ("C", "E"),
        ("D", "A"), ("D", "B"), ("D", "C"), ("D", "E"),
        ("E", "B"), ("E", "D")
    ]:
        x[(from_node, to_node)] = model.addVar(name=variables_keys[f"x_{from_node}_{to_node}"], vtype=GRB.BINARY)

    # Objective function: Maximize bottleneck bandwidth
    model.setObjective(z, GRB.MAXIMIZE)

    # Define bandwidth
    for (from_node, to_node) in [
        ("A", "B"), ("A", "C"), ("A", "E"),
        ("B", "A"), ("B", "C"), ("B", "D"), ("B", "E"),
        ("C", "A"), ("C", "D"), ("C", "E"),
        ("D", "A"), ("D", "B"), ("D", "C"), ("D", "E"),
        ("E", "B"), ("E", "D")
    ]:
        model.addConstr(x[(from_node, to_node)] * bandwidth[from_node][to_node] >= z)

    # Flow conservation for node A
    model.addConstr(gp.quicksum(x[(from_node, "A")] for from_node in nodes if (from_node, "A") in x.keys()) <= 1)

    # Flow conservation for node E
    model.addConstr(gp.quicksum(x[("E", to_node)] for to_node in nodes if ("E", to_node) in x.keys()) <= 1)

    # Flow conservation for node C (must be visited)
    model.addConstr(gp.quicksum(x[("A", to_node)] for to_node in nodes if ("A", to_node) in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("to_node", "A")] for to_node in nodes if ("to_node", "A") in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("B", to_node)] for to_node in nodes if ("B", to_node) in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("to_node", "B")] for to_node in nodes if ("to_node", "B") in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("C", to_node)] for to_node in nodes if ("C", to_node) in x.keys()) == 1)
    model.addConstr(gp.quicksum(x[("to_node", "C")] for to_node in nodes if ("to_node", "C") in x.keys()) == 1)
    model.addConstr(gp.quicksum(x[("D", to_node)] for to_node in nodes if ("D", to_node) in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("to_node", "D")] for to_node in nodes if ("to_node", "D") in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("E", to_node)] for to_node in nodes if ("E", to_node) in x.keys() and to_node != "C") <= 1)
    model.addConstr(gp.quicksum(x[("to_node", "E")] for to_node in nodes if ("to_node", "E") in x.keys() and to_node != "C") <= 1)

    return model, x

def solve(data: dict) -> dict:
    model, x = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "z": model.objVal,
            "x_A_B": x[("A", "B")].x,
            "x_A_C": x[("A", "C")].x,
            "x_A_E": x[("A", "E")].x,
            "x_B_A": x[("B", "A")].x,
            "x_B_C": x[("B", "C")].x,
            "x_B_D": x[("B", "D")].x,
            "x_B_E": x[("B", "E")].x,
            "x_C_A": x[("C", "A")].x,
            "x_C_D": x[("C", "D")].x,
            "x_C_E": x[("C", "E")].x,
            "x_D_A": x[("D", "A")].x,
            "x_D_B": x[("D", "B")].x,
            "x_D_C": x[("D", "C")].x,
            "x_D_E": x[("D", "E")].x,
            "x_E_B": x[("E", "B")].x,
            "x_E_D": x[("E", "D")].x
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