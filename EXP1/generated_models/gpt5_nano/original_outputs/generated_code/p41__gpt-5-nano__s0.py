import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Decision variables
    produce_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_solid")

    # Parameters from data
    init_liq = data["initial_inventory"]["liquid"]
    init_sol = data["initial_inventory"]["solid"]
    dem_liq = data["demand"]["liquid"]
    dem_sol = data["demand"]["solid"]

    m1_liq = data["machine_minutes"]["machine1"]["liquid"]
    m1_sol = data["machine_minutes"]["machine1"]["solid"]
    m2_liq = data["machine_minutes"]["machine2"]["liquid"]
    m2_sol = data["machine_minutes"]["machine2"]["solid"]

    m1_minutes = data["available_hours"]["machine1"] * 60
    m2_minutes = data["available_hours"]["machine2"] * 60

    # Resources constraints
    model.addConstr(m1_liq * produce_liquid + m1_sol * produce_solid <= m1_minutes, name="Machine1")
    model.addConstr(m2_liq * produce_liquid + m2_sol * produce_solid <= m2_minutes, name="Machine2")

    # Inventory balance (ending inventory)
    model.addConstr(ending_liquid == init_liq + produce_liquid - dem_liq, name="Balance_liq")
    model.addConstr(ending_solid == init_sol + produce_solid - dem_sol, name="Balance_sol")

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

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    model.update()
    objective = model.ObjVal

    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }

    return {
        "status": status,
        "objective": float(objective),
        "solution": solution
    }