import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    for start_month in data['months']:
        for length in data['contract_lengths']:
            if [start_month, length] not in data['feasible_start_length_pairs']:
                continue
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
                                  for start_month in data['months'] 
                                  for length in data['contract_lengths'] 
                                  if [start_month, length] in data['feasible_start_length_pairs'] 
                                  and month >= start_month and month < start_month + length)
        model.addConstr(demand_expr == data['demand_100sqm'][str(month)], name=f'demand_{month}')
    
    # At least two distinct lengths
    model.addConstr(gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths']) >= data['min_distinct_lengths'], 
                    name='at_least_two_lengths')
    
    # No more than three distinct lengths
    model.addConstr(gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths']) <= data['max_distinct_lengths'], 
                    name='no_more_than_three_lengths')
    
    # If a 4-month contract is chosen, then no 1-month contract may be chosen
    if 1 in data['mutually_exclusive_lengths'] and 4 in data['mutually_exclusive_lengths']:
        model.addConstr(variables[f'y_{data["mutually_exclusive_lengths"][0]}'] + variables[f'y_{data["mutually_exclusive_lengths"][1]}'] <= 1, 
                         name='no_1_and_4_month_contracts')
    
    # Link x and y variables
    for start_month in data['months']:
        for length in data['contract_lengths']:
            if [start_month, length] not in data['feasible_start_length_pairs']:
                continue
            model.addConstr(variables[f'x_{start_month}_{length}'] <= 1000 * variables[f'y_{length}'], 
                            name=f'link_x_y_{start_month}_{length}')
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    solution = {}
    for var_name in variables.keys():
        solution[var_name] = variables[var_name].X
    
    status_map = {gp.GRB.OPTIMAL: 'OPTIMAL', gp.GRB.INFEASIBLE: 'INFEASIBLE', 
                  gp.GRB.UNBOUNDED: 'UNBOUNDED', gp.GRB.INF_OR_UNBD: 'INF_OR_UNBD'}
    result = {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }
    
    return result