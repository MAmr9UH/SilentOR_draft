import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("two_machines_fertilizers")

    # Extract data
    initial_liquid = data["initial_inventory"]["liquid"]
    initial_solid = data["initial_inventory"]["solid"]
    demand_liquid = data["demand"]["liquid"]
    demand_solid = data["demand"]["solid"]

    M1_capacity = data["available_hours"]["machine1"] * 60.0  # minutes
    M2_capacity = data["available_hours"]["machine2"] * 60.0  # minutes

    t_M1_liq = data["machine_minutes"]["machine1"]["liquid"]
    t_M1_sol = data["machine_minutes"]["machine1"]["solid"]
    t_M2_liq = data["machine_minutes"]["machine2"]["liquid"]
    t_M2_sol = data["machine_minutes"]["machine2"]["solid"]

    # Decision variables
    produce_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="ending_solid")

    # Balance constraints
    model.addConstr(ending_liquid == initial_liquid + produce_liquid - demand_liquid, name="balance_liq")
    model.addConstr(ending_solid == initial_solid + produce_solid - demand_solid, name="balance_sol")

    # Machine capacity constraints
    model.addConstr(t_M1_liq * produce_liquid + t_M1_sol * produce_solid <= M1_capacity, name="machine1_capacity")
    model.addConstr(t_M2_liq * produce_liquid + t_M2_sol * produce_solid <= M2_capacity, name="machine2_capacity")

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)

    model.update()

    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }.get(status_code, str(status_code))

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }