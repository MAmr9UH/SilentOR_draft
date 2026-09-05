import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        for month in data['months']:
            variables[f'buy_{oil}_{month}'] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
            variables[f'use_{oil}_{month}'] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
            variables[f'store_{oil}_{month}'] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
            variables[f'y_{oil}_{month}'] = model.addVar(vtype=gp.GRB.BINARY)
    
    # Objective function
    obj_expr = gp.quicksum(
        (data['sell_price'] * variables[f'use_{oil}_{month}']) 
        - data['purchase_price'][month][oil] * variables[f'buy_{oil}_{month}']
        - data['storage_cost_per_ton_month'] * variables[f'store_{oil}_{month}']
        for oil in data['vegetable_oils'] + data['non_vegetable_oils']
        for month in data['months']
    )
    
    model.setObjective(obj_expr, gp.GRB.MAXIMIZE)
    
    # Constraints
    for month in data['months']:
        veg_refine = gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['vegetable_oils'])
        nonveg_refine = gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['non_vegetable_oils'])
        
        model.addConstr(veg_refine <= data['veg_refine_cap'], f'veg_refine_cap_{month}')
        model.addConstr(nonveg_refine <= data['nonveg_refine_cap'], f'nonveg_refine_cap_{month}')
        
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        for month in data['months']:
            if month == 'Jan':
                model.addConstr(variables[f'store_{oil}_{month}'] == data['initial_storage_per_oil'] + variables[f'buy_{oil}_{month}'] - variables[f'use_{oil}_{month}'])
            else:
                prev_month = data['months'][data['months'].index(month) - 1]
                model.addConstr(variables[f'store_{oil}_{month}'] == variables[f'store_{oil}_{prev_month}'] + variables[f'buy_{oil}_{month}'] - variables[f'use_{oil}_{month}'])
        
        last_month = data['months'][-1]
        model.addConstr(variables[f'store_{oil}_{last_month}'] >= data['required_final_storage_per_oil'], f'required_final_storage_{oil}')
    
    for month in data['months']:
        oils_used = gp.quicksum(variables[f'y_{oil}_{month}'] for oil in data['vegetable_oils'] + data['non_vegetable_oils'])
        model.addConstr(oils_used <= 3, f'at_most_3_oils_{month}')
        
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        for month in data['months']:
            model.addConstr(variables[f'use_{oil}_{month}'] >= 20 * variables[f'y_{oil}_{month}'], f'at_least_20_tons_{oil}_{month}')
    
    for month in data['months']:
        veg1_used = variables[f'y_VEG1_{month}']
        veg2_used = variables[f'y_VEG2_{month}']
        oil3_used = variables[f'y_OIL3_{month}']
        
        model.addConstr(veg1_used + veg2_used <= oil3_used, f'veg_oils_require_oil3_{month}')
    
    for month in data['months']:
        total_hardness = gp.quicksum(variables[f'use_{oil}_{month}'] * data['hardness'][oil] for oil in data['vegetable_oils'] + data['non_vegetable_oils'])
        model.addConstr(total_hardness >= data['min_hardness'] * gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['vegetable_oils'] + data['non_vegetable_oils']), f'min_hardness_{month}')
        model.addConstr(total_hardness <= data['max_hardness'] * gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['vegetable_oils'] + data['non_vegetable_oils']), f'max_hardness_{month}')
    
    return model, variables

def solve_model(data: dict) -> dict:
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
    
    solution = {
        'status': status,
        'objective_value': model.ObjVal if status == 'OPTIMAL' else None,
        'solution': {var_name: var.X for var_name, var in variables.items()}
    }
    
    return solution