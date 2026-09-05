import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        for month in data['months']:
            variables[f'buy_{oil}_{month}'] = model.addVar(lb=0, ub=data['storage_cap_per_oil'], vtype=gp.GRB.CONTINUOUS)
            variables[f'use_{oil}_{month}'] = model.addVar(lb=0, ub=data['storage_cap_per_oil'], vtype=gp.GRB.CONTINUOUS)
            variables[f'store_{oil}_{month}'] = model.addVar(lb=0, ub=data['storage_cap_per_oil'], vtype=gp.GRB.CONTINUOUS)
            variables[f'y_{oil}_{month}'] = model.addVar(vtype=gp.GRB.BINARY)
    
    # Objective function
    obj = gp.quicksum(variables[f'buy_{oil}_{month}'] * data['purchase_price'][month][oil] for oil in data['vegetable_oils'] + data['non_vegetable_oils'] for month in data['months'])
    obj -= gp.quicksum(data['sell_price'] * variables[f'use_{oil}_{month}'] for oil in data['vegetable_oils'] + data['non_vegetable_oils'] for month in data['months'])
    obj += gp.quicksum(variables[f'store_{oil}_{month}'] * data['storage_cost_per_ton_month'] for oil in data['vegetable_oils'] + data['non_vegetable_oils'] for month in data['months'])
    
    model.setObjective(obj, gp.GRB.MINIMIZE)
    
    # Constraints
    for month in data['months']:
        veg_refine = gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['vegetable_oils'])
        nonveg_refine = gp.quicksum(variables[f'use_{oil}_{month}'] for oil in data['non_vegetable_oils'])
        
        model.addConstr(veg_refine <= data['veg_refine_cap'], f'veg_refine_cap_{month}')
        model.addConstr(nonveg_refine <= data['nonveg_refine_cap'], f'nonveg_refine_cap_{month}')
    
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        for month in data['months']:
            if month == 'Jan':
                model.addConstr(variables[f'store_{oil}_{month}'] == variables[f'buy_{oil}_{month}'] + data['initial_storage_per_oil'] - variables[f'use_{oil}_{month}'], f'storage_balance_{oil}_{month}')
            else:
                prev_month = data['months'][data['months'].index(month) - 1]
                model.addConstr(variables[f'store_{oil}_{month}'] == variables[f'store_{oil}_{prev_month}'] + variables[f'buy_{oil}_{month}'] - variables[f'use_{oil}_{month}'], f'storage_balance_{oil}_{month}')
    
    for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
        model.addConstr(variables[f'store_{oil}_Jun'] == data['required_final_storage_per_oil'], f'final_storage_{oil}')
    
    for month in data['months']:
        num_oils_used = gp.quicksum(variables[f'y_{oil}_{month}'] for oil in data['vegetable_oils'] + data['non_vegetable_oils'])
        model.addConstr(num_oils_used <= 3, f'at_most_3_oils_{month}')
        
        for oil in data['vegetable_oils'] + data['non_vegetable_oils']:
            model.addConstr(variables[f'use_{oil}_{month}'] >= 20 * variables[f'y_{oil}_{month}'], f'min_use_{oil}_{month}')
    
    for month in data['months']:
        veg1_used = variables[f'y_VEG1_{month}']
        veg2_used = variables[f'y_VEG2_{month}']
        oil3_used = variables[f'y_OIL3_{month}']
        
        model.addConstr(veg1_used + veg2_used <= oil3_used, f'veg_oil_restrictions_{month}')
    
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

data = {
    "vegetable_oils": [
        "VEG1",
        "VEG2"
    ],
    "non_vegetable_oils": [
        "OIL1",
        "OIL2",
        "OIL3"
    ],
    "months": [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun"
    ],
    "purchase_price": {
        "Jan": {
            "VEG1": 110,
            "VEG2": 120,
            "OIL1": 130,
            "OIL2": 110,
            "OIL3": 115
        },
        "Feb": {
            "VEG1": 130,
            "VEG2": 130,
            "OIL1": 110,
            "OIL2": 90,
            "OIL3": 115
        },
        "Mar": {
            "VEG1": 110,
            "VEG2": 140,
            "OIL1": 130,
            "OIL2": 100,
            "OIL3": 95
        },
        "Apr": {
            "VEG1": 120,
            "VEG2": 110,
            "OIL1": 120,
            "OIL2": 120,
            "OIL3": 125
        },
        "May": {
            "VEG1": 100,
            "VEG2": 120,
            "OIL1": 150,
            "OIL2": 110,
            "OIL3": 105
        },
        "Jun": {
            "VEG1": 90,
            "VEG2": 100,
            "OIL1": 140,
            "OIL2": 80,
            "OIL3": 135
        }
    },
    "sell_price": 150,
    "veg_refine_cap": 200,
    "nonveg_refine_cap": 250,
    "storage_cap_per_oil": 1000,
    "storage_cost_per_ton_month": 5,
    "hardness": {
        "VEG1": 8.8,
        "VEG2": 6.1,
        "OIL1": 2.0,
        "OIL2": 4.2,
        "OIL3": 5.0
    },
    "min_hardness": 3,
    "max_hardness": 6,
    "initial_storage_per_oil": 500,
    "required_final_storage_per_oil": 500,
    "logical_restrictions": [
        "at most 3 oils used per month",
        "if an oil is used, >= 20 tons of it",
        "if VEG1 or VEG2 used, OIL3 must be used"
    ]
}

solution = solve_model(data)
print(solution)