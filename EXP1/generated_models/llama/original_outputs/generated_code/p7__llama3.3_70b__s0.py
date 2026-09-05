import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {
        "x_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "x_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Iv_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_I_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_II_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_1": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_2": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_3": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS),
        "Bk_III_4": model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    }
    
    # Block production of product I in quarter 2
    variables["x_I_2"].ub = 0
    
    # Objective function: minimize total late-penalty and storage cost
    obj_expr = gp.quicksum([data['late_penalty_per_unit_per_quarter']['I'] * variables[f"Bk_I_{q}"] for q in data['quarters']]) + \
               gp.quicksum([data['late_penalty_per_unit_per_quarter']['II'] * variables[f"Bk_II_{q}"] for q in data['quarters']]) + \
               gp.quicksum([data['late_penalty_per_unit_per_quarter']['III'] * variables[f"Bk_III_{q}"] for q in data['quarters']]) + \
               gp.quicksum([data['storage_cost_per_unit_per_quarter'] * variables[f"Iv_I_{q}"] for q in data['quarters']]) + \
               gp.quicksum([data['storage_cost_per_unit_per_quarter'] * variables[f"Iv_II_{q}"] for q in data['quarters']]) + \
               gp.quicksum([data['storage_cost_per_unit_per_quarter'] * variables[f"Iv_III_{q}"] for q in data['quarters']])
    model.setObjective(obj_expr, gp.GRB.MINIMIZE)
    
    # Constraints
    # Production capacity constraints
    for q in data['quarters']:
        production_hours = gp.quicksum([data['hours_per_unit']['I'] * variables[f"x_I_{q}"], 
                                         data['hours_per_unit']['II'] * variables[f"x_II_{q}"], 
                                         data['hours_per_unit']['III'] * variables[f"x_III_{q}"]])
        model.addConstr(production_hours <= data['capacity_hours_per_quarter'])
    
    # Inventory balance constraints
    for p in data['products']:
        if p == 'I':
            model.addConstr(variables["x_I_1"] - data['orders'][f"I_1"] + variables[f"Iv_I_1"] == 0)
            model.addConstr(variables["x_I_2"] - data['orders'][f"I_2"] + variables[f"Iv_I_1"] - variables[f"Bk_I_1"] + variables[f"Iv_I_2"] == 0)
            model.addConstr(variables["x_I_3"] - data['orders'][f"I_3"] + variables[f"Iv_I_2"] - variables[f"Bk_I_2"] + variables[f"Iv_I_3"] == 0)
            model.addConstr(variables["x_I_4"] - data['orders'][f"I_4"] + variables[f"Iv_I_3"] - variables[f"Bk_I_3"] + variables[f"Iv_I_4"] == 0)
        elif p == 'II':
            model.addConstr(variables["x_II_1"] - data['orders'][f"II_1"] + variables[f"Iv_II_1"] == 0)
            model.addConstr(variables["x_II_2"] - data['orders'][f"II_2"] + variables[f"Iv_II_1"] - variables[f"Bk_II_1"] + variables[f"Iv_II_2"] == 0)
            model.addConstr(variables["x_II_3"] - data['orders'][f"II_3"] + variables[f"Iv_II_2"] - variables[f"Bk_II_2"] + variables[f"Iv_II_3"] == 0)
            model.addConstr(variables["x_II_4"] - data['orders'][f"II_4"] + variables[f"Iv_II_3"] - variables[f"Bk_II_3"] + variables[f"Iv_II_4"] == 0)
        elif p == 'III':
            model.addConstr(variables["x_III_1"] - data['orders'][f"III_1"] + variables[f"Iv_III_1"] == 0)
            model.addConstr(variables["x_III_2"] - data['orders'][f"III_2"] + variables[f"Iv_III_1"] - variables[f"Bk_III_1"] + variables[f"Iv_III_2"] == 0)
            model.addConstr(variables["x_III_3"] - data['orders'][f"III_3"] + variables[f"Iv_III_2"] - variables[f"Bk_III_2"] + variables[f"Iv_III_3"] == 0)
            model.addConstr(variables["x_III_4"] - data['orders'][f"III_4"] + variables[f"Iv_III_3"] - variables[f"Bk_III_3"] + variables[f"Iv_III_4"] == 0)
    
    # Required ending inventory constraints
    for p in data['products']:
        if p == 'I':
            model.addConstr(variables["Iv_I_4"] >= data['required_ending_inventory'])
        elif p == 'II':
            model.addConstr(variables["Iv_II_4"] >= data['required_ending_inventory'])
        elif p == 'III':
            model.addConstr(variables["Iv_III_4"] >= data['required_ending_inventory'])
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: 'OPTIMAL',
        gp.GRB.INFEASIBLE: 'INFEASIBLE',
        gp.GRB.UNBOUNDED: 'UNBOUNDED',
        gp.GRB.INF_OR_UNBD: 'INF_OR_UNBD',
        gp.GRB.TIME_LIMIT: 'TIME_LIMIT'
    }
    
    solution = {
        "x_I_1": variables["x_I_1"].X,
        "x_I_2": variables["x_I_2"].X,
        "x_I_3": variables["x_I_3"].X,
        "x_I_4": variables["x_I_4"].X,
        "x_II_1": variables["x_II_1"].X,
        "x_II_2": variables["x_II_2"].X,
        "x_II_3": variables["x_II_3"].X,
        "x_II_4": variables["x_II_4"].X,
        "x_III_1": variables["x_III_1"].X,
        "x_III_2": variables["x_III_2"].X,
        "x_III_3": variables["x_III_3"].X,
        "x_III_4": variables["x_III_4"].X,
        "Iv_I_1": variables["Iv_I_1"].X,
        "Iv_I_2": variables["Iv_I_2"].X,
        "Iv_I_3": variables["Iv_I_3"].X,
        "Iv_I_4": variables["Iv_I_4"].X,
        "Iv_II_1": variables["Iv_II_1"].X,
        "Iv_II_2": variables["Iv_II_2"].X,
        "Iv_II_3": variables["Iv_II_3"].X,
        "Iv_II_4": variables["Iv_II_4"].X,
        "Iv_III_1": variables["Iv_III_1"].X,
        "Iv_III_2": variables["Iv_III_2"].X,
        "Iv_III_3": variables["Iv_III_3"].X,
        "Iv_III_4": variables["Iv_III_4"].X,
        "Bk_I_1": variables["Bk_I_1"].X,
        "Bk_I_2": variables["Bk_I_2"].X,
        "Bk_I_3": variables["Bk_I_3"].X,
        "Bk_I_4": variables["Bk_I_4"].X,
        "Bk_II_1": variables["Bk_II_1"].X,
        "Bk_II_2": variables["Bk_II_2"].X,
        "Bk_II_3": variables["Bk_II_3"].X,
        "Bk_II_4": variables["Bk_II_4"].X,
        "Bk_III_1": variables["Bk_III_1"].X,
        "Bk_III_2": variables["Bk_III_2"].X,
        "Bk_III_3": variables["Bk_III_3"].X,
        "Bk_III_4": variables["Bk_III_4"].X
    }
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }