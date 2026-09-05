import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "prod_I_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_I_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_I_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_I_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_I_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_I_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "prod_II_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_I_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "inv_II_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "own_storage_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_7": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_8": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_9": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_10": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_11": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "external_storage_12": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    }
    
    # Production capacity constraints
    for month in data["months"]:
        prod_I = variables[f"prod_I_{month}"]
        prod_II = variables[f"prod_II_{month}"]
        model.addConstr(prod_I + prod_II <= data["monthly_total_production_capacity"])
        
    # Demand constraints
    inv_I_prev = data["initial_inventory"]["I"]
    inv_II_prev = data["initial_inventory"]["II"]
    for month in data["months"]:
        demand_I = data["demand"]["I"][f"{month}"]
        demand_II = data["demand"]["II"][f"{month}"]
        prod_I = variables[f"prod_I_{month}"]
        prod_II = variables[f"prod_II_{month}"]
        inv_I = variables[f"inv_I_{month}"]
        inv_II = variables[f"inv_II_{month}"]
        
        model.addConstr(inv_I_prev + prod_I - demand_I == inv_I)
        model.addConstr(inv_II_prev + prod_II - demand_II == inv_II)
        
        inv_I_prev = inv_I
        inv_II_prev = inv_II
        
    # Inventory volume constraints
    for month in data["months"]:
        own_storage = variables[f"own_storage_{month}"]
        external_storage = variables[f"external_storage_{month}"]
        inv_I = variables[f"inv_I_{month}"]
        inv_II = variables[f"inv_II_{month}"]
        
        model.addConstr(own_storage + external_storage == data["unit_volume"]["I"] * inv_I + data["unit_volume"]["II"] * inv_II)
        model.addConstr(own_storage <= data["own_warehouse_capacity_cubic_m"])
        
    # Objective function
    obj = gp.quicksum(
        [variables[f"prod_I_{month}"] * data["production_cost"]["I"] for month in data["months"]]
        + [variables[f"prod_II_{month}"] * data["production_cost"]["II"] for month in data["months"]]
        + [variables[f"own_storage_{month}"] * data["own_storage_cost_per_cubic_m_month"] for month in data["months"]]
        + [variables[f"external_storage_{month}"] * data["external_storage_cost_per_cubic_m_month"] for month in data["months"]]
    )
    
    model.setObjective(obj, gp.GRB.MINIMIZE)
    
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
        "prod_I_7": variables["prod_I_7"].X,
        "prod_I_8": variables["prod_I_8"].X,
        "prod_I_9": variables["prod_I_9"].X,
        "prod_I_10": variables["prod_I_10"].X,
        "prod_I_11": variables["prod_I_11"].X,
        "prod_I_12": variables["prod_I_12"].X,
        "prod_II_7": variables["prod_II_7"].X,
        "prod_II_8": variables["prod_II_8"].X,
        "prod_II_9": variables["prod_II_9"].X,
        "prod_II_10": variables["prod_II_10"].X,
        "prod_II_11": variables["prod_II_11"].X,
        "prod_II_12": variables["prod_II_12"].X,
        "inv_I_7": variables["inv_I_7"].X,
        "inv_I_8": variables["inv_I_8"].X,
        "inv_I_9": variables["inv_I_9"].X,
        "inv_I_10": variables["inv_I_10"].X,
        "inv_I_11": variables["inv_I_11"].X,
        "inv_I_12": variables["inv_I_12"].X,
        "inv_II_7": variables["inv_II_7"].X,
        "inv_II_8": variables["inv_II_8"].X,
        "inv_II_9": variables["inv_II_9"].X,
        "inv_II_10": variables["inv_II_10"].X,
        "inv_II_11": variables["inv_II_11"].X,
        "inv_II_12": variables["inv_II_12"].X,
        "own_storage_7": variables["own_storage_7"].X,
        "own_storage_8": variables["own_storage_8"].X,
        "own_storage_9": variables["own_storage_9"].X,
        "own_storage_10": variables["own_storage_10"].X,
        "own_storage_11": variables["own_storage_11"].X,
        "own_storage_12": variables["own_storage_12"].X,
        "external_storage_7": variables["external_storage_7"].X,
        "external_storage_8": variables["external_storage_8"].X,
        "external_storage_9": variables["external_storage_9"].X,
        "external_storage_10": variables["external_storage_10"].X,
        "external_storage_11": variables["external_storage_11"].X,
        "external_storage_12": variables["external_storage_12"].X
    }
    
    return {
        "status": status,
        "objective": model.ObjVal,
        "solution": solution
    }