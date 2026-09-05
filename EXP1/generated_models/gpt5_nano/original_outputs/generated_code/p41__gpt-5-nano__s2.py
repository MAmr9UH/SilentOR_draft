import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Data extraction
    init_liq = data["initial_inventory"]["liquid"]
    init_sol = data["initial_inventory"]["solid"]
    demand_liq = data["demand"]["liquid"]
    demand_sol = data["demand"]["solid"]
    
    time1_liq = data["machine_minutes"]["machine1"]["liquid"]
    time1_sol = data["machine_minutes"]["machine1"]["solid"]
    time2_liq = data["machine_minutes"]["machine2"]["liquid"]
    time2_sol = data["machine_minutes"]["machine2"]["solid"]
    
    m1_minutes = data["available_hours"]["machine1"] * 60
    m2_minutes = data["available_hours"]["machine2"] * 60
    
    # Decision variables (flat continuous)
    produce_liquid = model.addVar(lb=0.0, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, name="ending_solid")
    
    # Constraints
    model.addConstr(time1_liq * produce_liquid + time1_sol * produce_solid <= m1_minutes, name="Machine1")
    model.addConstr(time2_liq * produce_liquid + time2_sol * produce_solid <= m2_minutes, name="Machine2")
    
    model.addConstr(init_liq + produce_liquid - demand_liq == ending_liquid, name="LiquidBalance")
    model.addConstr(init_sol + produce_solid - demand_sol == ending_solid, name="SolidBalance")
    
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
    
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)
    
    objective = float(model.ObjVal)
    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }
    
    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }