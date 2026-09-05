import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parameters from data
    initial_liquid = data["initial_inventory"]["liquid"]
    initial_solid = data["initial_inventory"]["solid"]
    demand_liquid = data["demand"]["liquid"]
    demand_solid = data["demand"]["solid"]

    minutes_m1 = data["available_hours"]["machine1"] * 60
    minutes_m2 = data["available_hours"]["machine2"] * 60

    # Time coefficients (minutes per lot)
    time_m1_liquid = data["machine_minutes"]["machine1"]["liquid"]
    time_m1_solid = data["machine_minutes"]["machine1"]["solid"]
    time_m2_liquid = data["machine_minutes"]["machine2"]["liquid"]
    time_m2_solid = data["machine_minutes"]["machine2"]["solid"]

    # Decision variables (flat, continuous)
    produce_liquid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="ending_solid")

    # Constraints
    model.addConstr(time_m1_liquid * produce_liquid + time_m1_solid * produce_solid <= minutes_m1, name="Machine1")
    model.addConstr(time_m2_liquid * produce_liquid + time_m2_solid * produce_solid <= minutes_m2, name="Machine2")

    model.addConstr(ending_liquid == initial_liquid + produce_liquid - demand_liquid, name="EndInvLiquid")
    model.addConstr(ending_solid == initial_solid + produce_solid - demand_solid, name="EndInvSolid")

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, sense=gp.GRB.MAXIMIZE)

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

    status = model.Status
    if status == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    objective_value = float(model.ObjVal)

    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }