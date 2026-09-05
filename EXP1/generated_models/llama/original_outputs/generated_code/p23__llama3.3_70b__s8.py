import gurobipy as gp

def solve(data):
    model = gp.Model()
    
    # Define variables
    w_vars = {}
    for i in range(len(data['components'])):
        for j in range(len(data['spare_levels'])):
            for k in range(len(data['spare_levels'])):
                if len(data['components']) == 3:
                    var_name = f"w_{i+1}_{j}_{k}"
                    w_vars[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
                elif len(data['components']) == 2:
                    var_name = f"w_{i+1}_{j}"
                    w_vars[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Define objective function
    obj_func = gp.quicksum([w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+1)] for i in range(len(data['components'])) 
                            for j in range(len(data['spare_levels'])) 
                            for k in range(len(data['spare_levels']))])
    
    # Define constraints
    model.addConstr(gp.quicksum([w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_weight'][str(i+1)] for i in range(len(data['components'])) 
                                 for j in range(len(data['spare_levels'])) 
                                 for k in range(len(data['spare_levels']))]) <= data['weight_limit'])
    
    model.addConstr(obj_func <= data['budget'])
    
    # Exactly one combination is selected
    if len(data['components']) == 3:
        model.addConstr(gp.quicksum([w_vars[f"w_{i+1}_{j}_{k}"] for i in range(len(data['components'])) 
                                     for j in range(len(data['spare_levels'])) 
                                     for k in range(len(data['spare_levels']))]) == 1)
    elif len(data['components']) == 2:
        model.addConstr(gp.quicksum([w_vars[f"w_{i+1}_{j}"] for i in range(len(data['components'])) 
                                     for j in range(len(data['spare_levels']))]) == 1)
    
    # Solve the model
    model.setObjective(obj_func, gp.GRB.MINIMIZE)
    model.optimize()
    
    variables = w_vars
    
    return {
        'status': model.Status,
        'obj_val': model.ObjVal,
        'variables': {var_name: var.X for var_name, var in variables.items()}
    }