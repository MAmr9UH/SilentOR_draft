import gurobipy as gp

def solve_model(data):
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
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+2)] * (data['spare_levels'][k] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
    )
    
    # Define constraints
    model.addConstr(gp.quicksum([w_vars[var_name] for var_name in w_vars]), gp.GRB.EQUAL, 1)
    
    budget_constraint = gp.quicksum(
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
        +
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_price'][str(i+2)] * (data['spare_levels'][k] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
    )
    model.addConstr(budget_constraint, gp.GRB.LESS_EQUAL, data['budget'])
    
    weight_constraint = gp.quicksum(
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_weight'][str(i+1)] * (data['spare_levels'][j] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
        +
        [w_vars[f"w_{i+1}_{j}_{k}"] * data['unit_weight'][str(i+2)] * (data['spare_levels'][k] + 1) 
         for i in range(len(data['components']) - 2) 
         for j in range(len(data['spare_levels'])) 
         for k in range(len(data['spare_levels']))]
    )
    model.addConstr(weight_constraint, gp.GRB.LESS_EQUAL, data['weight_limit'])
    
    # Set objective function
    model.setObjective(obj_func, gp.GRB.MAXIMIZE)
    
    # Optimize the model
    model.optimize()
    
    variables = w_vars
    
    return {
        'status': model.Status,
        'obj_val': model.ObjVal,
        'variables': {var_name: var.X for var_name, var in variables.items()}
    }