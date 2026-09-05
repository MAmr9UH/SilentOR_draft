import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables
    produce_liquid = model.addVar(vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(vtype=GRB.CONTINUOUS, name="ending_solid")

    # Objective function: Maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)

    # Constraints

    # Machine 1 time constraint
    machine1_time = data["available_hours"]["machine1"] * 60
    model.addConstr(
        data["machine_minutes"]["machine1"]["liquid"] * produce_liquid
        + data["machine_minutes"]["machine1"]["solid"] * produce_solid
        <= machine1_time,
        "Machine 1 time constraint",
    )

    # Machine 2 time constraint
    machine2_time = data["available_hours"]["machine2"] * 60
    model.addConstr(
        data["machine_minutes"]["machine2"]["liquid"] * produce_liquid
        + data["machine_minutes"]["machine2"]["solid"] * produce_solid
        <= machine2_time,
        "Machine 2 time constraint",
    )

    # Liquid demand and inventory constraints
    model.addConstr(
        ending_liquid <= data["demand"]["liquid"] + ending_liquid - produce_liquid
        + data["initial_inventory"]["liquid"],
        "Liquid demand constraint",
    )

    # Solid demand and inventory constraints
    model.addConstr(
        ending_solid <= data["demand"]["solid"] + ending_solid - produce_solid
        + data["initial_inventory"]["solid"],
        "Solid demand constraint",
    )

    # Non-negativity constraints
    model.addConstr(produce_liquid >= 0, "Produce liquid non-negativity")
    model.addConstr(produce_solid >= 0, "Produce solid non-negativity")
    model.addConstr(ending_liquid >= 0, "Ending liquid non-negativity")
    model.addConstr(ending_solid >= 0, "Ending solid non-negativity")

    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid,
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {},
        }

    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X),
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution,
    }