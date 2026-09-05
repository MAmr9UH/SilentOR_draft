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
    obj_func = gp.quicksum(
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
        +
        [w_vars[f"w_{i+1}_{j}"] * data['unit_price'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2, len(data['components'])) 
         for j in range(len(data['spare_levels']))]
    )
    
    # Define constraints
    model.addConstr(gp.quicksum([w_vars[var_name] for var_name in w_vars.keys()]) == 1)
    
    budget_constraint = gp.quicksum(
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
        +
        [w_vars[f"w_{i+1}_{j}"] * data['unit_price'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2, len(data['components'])) 
         for j in range(len(data['spare_levels']))]
    )
    model.addConstr(budget_constraint <= data['budget'])
    
    weight_limit_constraint = gp.quicksum(
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_weight'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
        +
        [w_vars[f"w_{i+1}_{j}"] * data['unit_weight'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2, len(data['components'])) 
         for j in range(len(data['spare_levels']))]
    )
    model.addConstr(weight_limit_constraint <= data['weight_limit'])
    
    # Set objective function
    model.setObjective(obj_func, gp.GRB.MINIMIZE)
    
    # Solve the model
    model.optimize()
    
    variables = {}
    for var_name in w_vars.keys():
        variables[var_name] = w_vars[var_name]
    
    return {
        'status': model.Status,
        'obj_val': model.ObjVal,
        'variables': variables
    }