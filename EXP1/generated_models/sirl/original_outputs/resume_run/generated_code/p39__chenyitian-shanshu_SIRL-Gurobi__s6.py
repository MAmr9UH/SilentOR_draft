import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("project_schedule_model")
    
    durations = data["durations"]
    activities = data["activities"]
    precedence = data["precedence"]
    work_cost_per_project_day = data["work_cost_per_project_day"]
    machine_rental_cost_per_day = data["machine_rental_cost_per_day"]
    machine_rental_from = data["machine_rental_from"]
    machine_rental_to = data["machine_rental_to"]

    variables_keys = {
        "start_A": "continuous timing variable in days",
        "start_B": "continuous timing variable in days",
        "start_C": "continuous timing variable in days",
        "start_D": "continuous timing variable in days",
        "start_E": "continuous timing variable in days",
        "start_F": "continuous timing variable in days",
        "start_G": "continuous timing variable in days",
        "Cmax": "continuous timing variable in days",
        "machine_span": "continuous timing variable in days"
    }

    variables = {}

    # Decision variables
    for key in variables_keys:
        variables[key] = model.addVar(name=key, vtype=GRB.CONTINUOUS, lb=0)

    # Cmax: completion time of the project
    model.addConstr(variables["Cmax"] >= variables["start_A"] + durations["A"])
    model.addConstr(variables["Cmax"] >= variables["start_B"] + durations["B"])
    model.addConstr(variables["Cmax"] >= variables["start_C"] + durations["C"])
    model.addConstr(variables["Cmax"] >= variables["start_D"] + durations["D"])
    model.addConstr(variables["Cmax"] >= variables["start_E"] + durations["E"])
    model.addConstr(variables["Cmax"] >= variables["start_F"] + durations["F"])
    model.addConstr(variables["Cmax"] >= variables["start_G"] + durations["G"])

    # Precedence constraints
    for (predecessor, successor) in precedence:
        if predecessor == "A" and successor == "G":
            model.addConstr(variables["start_G"] >= variables["start_A"] + durations["A"])
        elif predecessor == "A" and successor == "D":
            model.addConstr(variables["start_D"] >= variables["start_A"] + durations["A"])
        elif predecessor == "E" and successor == "F":
            model.addConstr(variables["start_F"] >= variables["start_E"] + durations["E"])
        elif predecessor == "G" and successor == "F":
            model.addConstr(variables["start_F"] >= variables["start_G"] + durations["G"])
        elif predecessor == "D" and successor == "C":
            model.addConstr(variables["start_C"] >= variables["start_D"] + durations["D"])
        elif predecessor == "F" and successor == "C":
            model.addConstr(variables["start_C"] >= variables["start_F"] + durations["F"])
        elif predecessor == "F" and successor == "B":
            model.addConstr(variables["start_B"] >= variables["start_F"] + durations["F"])

    # Objective function: minimize total project cost
    total_cost = gp.quicksum(work_cost_per_project_day * variables[activity] for activity in activities) \
                + machine_rental_cost_per_day * variables["machine_span"]

    model.setObjective(total_cost, GRB.MINIMIZE)

    # Define machine_span as end_B - start_A
    model.addConstr(variables["machine_span"] == variables["start_B"] - variables["start_A"])

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "start_A": variables["start_A"].x,
            "start_B": variables["start_B"].x,
            "start_C": variables["start_C"].x,
            "start_D": variables["start_D"].x,
            "start_E": variables["start_E"].x,
            "start_F": variables["start_F"].x,
            "start_G": variables["start_G"].x,
            "Cmax": variables["Cmax"].x,
            "machine_span": variables["machine_span"].x,
        }
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE" if model.status == GRB.INFEASIBLE else "OTHER",
            "objective": None,
            "solution": None
        }