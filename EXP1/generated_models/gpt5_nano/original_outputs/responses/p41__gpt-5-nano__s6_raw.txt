from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = __import__("gurobipy").Model()
    
    # Decision variables (continuous, >= 0)
    produce_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_solid")
    
    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }
    
    # Parameters from data
    initial_liquid = data["initial_inventory"]["liquid"]
    initial_solid = data["initial_inventory"]["solid"]
    demand_liquid = data["demand"]["liquid"]
    demand_solid = data["demand"]["solid"]
    machine1_minutes = data["machine_minutes"]["machine1"]
    machine2_minutes = data["machine_minutes"]["machine2"]
    available_hours1 = data["available_hours"]["machine1"]
    available_hours2 = data["available_hours"]["machine2"]
    
    # Constraints
    model.addConstr(50 * produce_liquid + 24 * produce_solid <= 60 * available_hours1)
    model.addConstr(30 * produce_liquid + 33 * produce_solid <= 60 * available_hours2)
    
    model.addConstr(ending_liquid == initial_liquid + produce_liquid - demand_liquid)
    model.addConstr(ending_solid == initial_solid + produce_solid - demand_solid)
    
    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)
    
    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Read results
    model.update()
    status = model.Status
    obj_val = model.ObjVal
    
    # Map status to string
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)
    
    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }
    
    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }