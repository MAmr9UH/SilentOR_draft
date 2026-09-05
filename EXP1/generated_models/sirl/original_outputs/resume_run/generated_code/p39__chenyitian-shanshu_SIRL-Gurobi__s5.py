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

    # Create decision variables
    for key in variables_keys:
        variables[key] = model.addVar(name=key, vtype=GRB.CONTINUOUS, lb=0)

    # Objective function: Minimize total project cost
    model.setObjective(
        gp.quicksum(durations[activity] * variables["start_" + activity] for activity in activities) +
        work_cost_per_project_day * variables["Cmax"] +
        machine_rental_cost_per_day * variables["machine_span"],
        GRB.MINIMIZE)

    # Activity durations
    for activity in activities:
        model.addConstr(variables["start_" + activity] >= 0)

    # Precedence constraints
    for predecessor, successor in precedence:
        model.addConstr(variables["start_" + successor] >= variables["start_" + predecessor] + durations[predecessor])

    # Cmax is the finish time of activity C
    model.addConstr(variables["start_C"] <= variables["Cmax"])

    # Machine rental from start of A to end of B
    model.addConstr(variables["machine_span"] == variables["start_B"] - variables["start_A"])

    model.update()
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
            "machine_span": variables["machine_span"].x
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