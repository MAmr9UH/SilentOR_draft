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
    
    # Objective
    objective = gp.quicksum(variables[f'x_{start_month}_{length}'] * data['fee_per_100sqm_by_length'][str(length)] 
                            for start_month in data['months'] 
                            for length in data['contract_lengths'] 
                            if [start_month, length] in data['feasible_start_length_pairs'])
    model.setObjective(objective)
    
    # Demand constraints
    for month in data['months']:
        demand = data['demand_100sqm'][str(month)]
        contracts_covering_month = gp.quicksum(variables[f'x_{start_month}_{length}'] 
                                               for start_month in range(1, 5) 
                                               for length in data['contract_lengths'] 
                                               if [start_month, length] in data['feasible_start_length_pairs'] 
                                               and month >= start_month and month < start_month + length)
        model.addConstr(contracts_covering_month == demand)
    
    # At least two distinct lengths
    at_least_two_lengths = gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths'])
    model.addConstr(at_least_two_lengths >= data['min_distinct_lengths'])
    
    # No more than three distinct lengths
    no_more_than_three_lengths = gp.quicksum(variables[f'y_{length}'] for length in data['contract_lengths'])
    model.addConstr(no_more_than_three_lengths <= data['max_distinct_lengths'])
    
    # If a 4-month contract is chosen, then no 1-month contract may be chosen
    if 1 in data['mutually_exclusive_lengths'] and 4 in data['mutually_exclusive_lengths']:
        model.addConstr(variables[f'y_{data["mutually_exclusive_lengths"][0]}'] + variables[f'y_{data["mutually_exclusive_lengths"][1]}'] <= 1)
    
    # Linking constraints
    for start_month in data['months']:
        for length in data['contract_lengths']:
            if [start_month, length] not in data['feasible_start_length_pairs']:
                continue
            model.addConstr(variables[f'x_{start_month}_{length}'] <= 100 * variables[f'y_{length}'])
    
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
    
    solution = {var_name: variables[var_name].X for var_name in variables}
    objective = model.ObjVal
    
    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }