import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    for start_month in data['months']:
        for length in data['contract_lengths']:
            if [start_month, length] in data['feasible_start_length_pairs']:
                var_name = f'x_{start_month}_{length}'
                variables[var_name] = model.addVar(vtype=gp.GRB.INTEGER, name=var_name)
    
    for length in data['contract_lengths']:
        var_name = f'y_{length}'
        variables[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Objective function
    obj_expr = gp.quicksum(variables[f'x_{start_month}_{length}'] * data['fee_per_100sqm_by_length'][str(length)] 
                           for start_month in data['months'] 
                           for length in data['contract_lengths'] 
                           if [start_month, length] in data['feasible_start_length_pairs'])
    model.setObjective(obj_expr, gp.GRB.MINIMIZE)
    
    # Demand constraints
    for month in data['months']:
        demand_expr = gp.quicksum(variables[f'x_{start_month}_{length}'] 
                                  for start_month in range(1, 5) 
                                  for length in data['contract_lengths'] 
                                  if [start_month, length] in data['feasible_start_length_pairs'] 
                                  and month >= start_month and month < start_month + length)
        model.addConstr(demand_expr == data['demand_100sqm'][str(month)], name=f'demand_{month}')
    
    # At least two distinct lengths
    min_distinct_lengths_expr = gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths'])
    model.addConstr(min_distinct_lengths_expr >= data['min_distinct_lengths'], name='min_distinct_lengths')
    
    # No more than three distinct lengths
    max_distinct_lengths_expr = gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths'])
    model.addConstr(max_distinct_lengths_expr <= data['max_distinct_lengths'], name='max_distinct_lengths')
    
    # Mutual exclusivity constraints
    for length1, length2 in zip(data['mutually_exclusive_lengths'][::2], data['mutually_exclusive_lengths'][1::2]):
        model.addConstr(variables[f'y_{length1}'] + variables[f'y_{length2}'] <= 1, name=f'mutual_exclusivity_{length1}_{length2}')
    
    # Linking constraints between x and y
    for start_month in data['months']:
        for length in data['contract_lengths']:
            if [start_month, length] in data['feasible_start_length_pairs']:
                model.addConstr(variables[f'x_{start_month}_{length}'] <= 1000 * variables[f'y_{length}'], name=f'linking_{start_month}_{length}')
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status = None
    if model.Status == gp.GRB.OPTIMAL:
        status = 'OPTIMAL'
    elif model.Status == gp.GRB.INFEASIBLE:
        status = 'INFEASIBLE'
    elif model.Status == gp.GRB.UNBOUNDED:
        status = 'UNBOUNDED'
    elif model.Status == gp.GRB.INF_OR_UNBD:
        status = 'INF_OR_UNBD'
    elif model.Status == gp.GRB.TIME_LIMIT:
        status = 'TIME_LIMIT'
    
    solution = {var_name: var.X for var_name, var in variables.items()}
    
    return {
        'status': status,
        'objective': model.ObjVal,
        'solution': solution
    }