import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("raw_material_transport_model")

    trucks_A = model.addVar(name="trucks_A", vtype=GRB.INTEGER, lb=0)
    trucks_B = model.addVar(name="trucks_B", vtype=GRB.INTEGER, lb=0)

    variables = {
        "trucks_A": trucks_A,
        "trucks_B": trucks_B
    }

    # Raw material A constraint
    model.addConstr(4 * trucks_A + 7 * trucks_B >= 240)

    # Raw material B constraint
    model.addConstr(2 * trucks_A + 2 * trucks_B >= 80)

    # Raw material C constraint
    model.addConstr(6 * trucks_A + 2 * trucks_B >= 120)

    # Objective function: Minimize total freight cost
    model.setObjective(200 * trucks_A + 160 * trucks_B, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "trucks_A": variables["trucks_A"].x,
                "trucks_B": variables["trucks_B"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "trucks_A": None,
                "trucks_B": None
            }
        }