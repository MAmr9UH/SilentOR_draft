import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    # Extract parameters from data
    I_liq0 = data["initial_inventory"]["liquid"]
    I_sol0 = data["initial_inventory"]["solid"]
    D_liq = data["demand"]["liquid"]
    D_sol = data["demand"]["solid"]

    m1_liq = data["machine_minutes"]["machine1"]["liquid"]
    m1_sol = data["machine_minutes"]["machine1"]["solid"]
    m2_liq = data["machine_minutes"]["machine2"]["liquid"]
    m2_sol = data["machine_minutes"]["machine2"]["solid"]

    avail_m1 = data["available_hours"]["machine1"] * 60  # convert hours to minutes
    avail_m2 = data["available_hours"]["machine2"] * 60

    # Create model
    model = gp.Model("TwoMachines_Fertilizers")

    # Decision variables (as per required keys)
    produce_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_solid")

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)

    # Constraints
    # Machine 1 capacity
    model.addConstr(m1_liq * produce_liquid + m1_sol * produce_solid <= avail_m1, name="Mach1_Capacity")

    # Machine 2 capacity
    model.addConstr(m2_liq * produce_liquid + m2_sol * produce_solid <= avail_m2, name="Mach2_Capacity")

    # Inventory balance / ending inventories
    model.addConstr(ending_liquid == I_liq0 + produce_liquid - D_liq, name="Balance_Liquid")
    model.addConstr(ending_solid  == I_sol0 + produce_solid - D_sol,  name="Balance_Solid")

    # Return model and variables in required structure
    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = model.ObjVal

    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid":  float(variables["produce_solid"].X),
        "ending_liquid":  float(variables["ending_liquid"].X),
        "ending_solid":   float(variables["ending_solid"].X)
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }