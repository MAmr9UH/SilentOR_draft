import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "x_1_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_1_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_2_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_2_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "z_1_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "z_1_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "z_2_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "z_2_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "y_1": model.addVar(vtype=gp.GRB.BINARY),
        "y_2": model.addVar(vtype=gp.GRB.BINARY)
    }
    
    # Constraints
    model.addConstr(variables["x_1_1"] + variables["x_1_2"], gp.GRB.EQUAL, data["supply"]["1"])
    model.addConstr(variables["x_2_1"] + variables["x_2_2"], gp.GRB.EQUAL, data["supply"]["2"])
    
    model.addConstr(variables["z_1_1"] + variables["z_2_1"], gp.GRB.EQUAL, data["demand"]["1"])
    model.addConstr(variables["z_1_2"] + variables["z_2_2"], gp.GRB.EQUAL, data["demand"]["2"])
    
    model.addConstr(variables["x_1_1"] + variables["x_2_1"], gp.GRB.LESS_OR_EQUAL, data["station_capacity"]["1"])
    model.addConstr(variables["x_1_2"] + variables["x_2_2"], gp.GRB.LESS_OR_EQUAL, data["station_capacity"]["2"])
    
    model.addConstr(variables["z_1_1"] + variables["z_1_2"], gp.GRB.EQUAL, variables["x_1_1"] + variables["x_2_1"])
    model.addConstr(variables["z_2_1"] + variables["z_2_2"], gp.GRB.EQUAL, variables["x_1_2"] + variables["x_2_2"])
    
    model.addConstr(variables["x_1_1"] + variables["x_2_1"], gp.GRB.LESS_OR_EQUAL, data["station_capacity"]["1"] * variables["y_1"])
    model.addConstr(variables["x_1_2"] + variables["x_2_2"], gp.GRB.LESS_OR_EQUAL, data["station_capacity"]["2"] * variables["y_2"])
    
    # Objective
    obj = (data["cost_source_station"]["1,1"] * variables["x_1_1"] +
           data["cost_source_station"]["1,2"] * variables["x_1_2"] +
           data["cost_source_station"]["2,1"] * variables["x_2_1"] +
           data["cost_source_station"]["2,2"] * variables["x_2_2"] +
           data["cost_station_demand"]["1,1"] * variables["z_1_1"] +
           data["cost_station_demand"]["1,2"] * variables["z_1_2"] +
           data["cost_station_demand"]["2,1"] * variables["z_2_1"] +
           data["cost_station_demand"]["2,2"] * variables["z_2_2"] +
           data["fixed_cost"]["1"] * variables["y_1"] +
           data["fixed_cost"]["2"] * variables["y_2"])
    
    model.setObjective(obj)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status = None
    if model.Status == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif model.Status == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif model.Status == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif model.Status == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif model.Status == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    
    solution = {
        "x_1_1": variables["x_1_1"].X,
        "x_1_2": variables["x_1_2"].X,
        "x_2_1": variables["x_2_1"].X,
        "x_2_2": variables["x_2_2"].X,
        "z_1_1": variables["z_1_1"].X,
        "z_1_2": variables["z_1_2"].X,
        "z_2_1": variables["z_2_1"].X,
        "z_2_2": variables["z_2_2"].X,
        "y_1": variables["y_1"].X,
        "y_2": variables["y_2"].X
    }
    
    return {
        "status": status,
        "objective": model.ObjVal,
        "solution": solution
    }