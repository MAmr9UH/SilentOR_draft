import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    for product in data['products']:
        for quarter in data['quarters']:
            variables[f'x_{product}_{quarter}'] = model.addVar(lb=0, vtype='C', name=f'x_{product}_{quarter}')
            variables[f'Iv_{product}_{quarter}'] = model.addVar(lb=0, vtype='C', name=f'Iv_{product}_{quarter}')
            variables[f'Bk_{product}_{quarter}'] = model.addVar(lb=0, vtype='C', name=f'Bk_{product}_{quarter}')

    for quarter in data['quarters']:
        production_hours = gp.quicksum([data['hours_per_unit'][product] * variables[f'x_{product}_{quarter}'] for product in data['products']])
        model.addConstr(production_hours <= data['capacity_hours_per_quarter'], name=f'production_capacity_{quarter}')

    for product in data['products']:
        if product == 'I':
            model.addConstr(variables[f'x_I_2'] == 0, name='product_I_blocked')
        
        for quarter_index, quarter in enumerate(data['quarters']):
            if quarter_index == 0:
                inventory = variables[f'Iv_{product}_{quarter}']
                backlog = variables[f'Bk_{product}_{quarter}']
                model.addConstr(inventory - data['initial_inventory'] + backlog == data['orders'][f'{product}_{quarter}'] - variables[f'x_{product}_{quarter}'], name=f'invent_backlog_balance_{product}_{quarter}')
            else:
                previous_quarter = data['quarters'][quarter_index - 1]
                inventory = variables[f'Iv_{product}_{quarter}']
                backlog = variables[f'Bk_{product}_{quarter}']
                model.addConstr(inventory + variables[f'Bk_{product}_{previous_quarter}'] == data['orders'][f'{product}_{quarter}'] + variables[f'Iv_{product}_{previous_quarter}'] - variables[f'x_{product}_{quarter}'], name=f'invent_backlog_balance_{product}_{quarter}')

    for product in data['products']:
        model.addConstr(variables[f'Iv_I_4'] == data['required_ending_inventory'], name='required_ending_inventory')
        model.addConstr(variables[f'Iv_II_4'] == data['required_ending_inventory'], name='required_ending_inventory')
        model.addConstr(variables[f'Iv_III_4'] == data['required_ending_inventory'], name='required_ending_inventory')

    objective = gp.quicksum([data['late_penalty_per_unit_per_quarter'][product] * variables[f'Bk_{product}_{quarter}'] for product in data['products'] for quarter in data['quarters']])
    objective += gp.quicksum([data['storage_cost_per_unit_per_quarter'] * variables[f'Iv_{product}_{quarter}'] for product in data['products'] for quarter in data['quarters']])
    
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    solution = {}
    for key in ['x_I_1', 'x_I_2', 'x_I_3', 'x_I_4',
                'x_II_1', 'x_II_2', 'x_II_3', 'x_II_4',
                'x_III_1', 'x_III_2', 'x_III_3', 'x_III_4',
                'Iv_I_1', 'Iv_I_2', 'Iv_I_3', 'Iv_I_4',
                'Iv_II_1', 'Iv_II_2', 'Iv_II_3', 'Iv_II_4',
                'Iv_III_1', 'Iv_III_2', 'Iv_III_3', 'Iv_III_4',
                'Bk_I_1', 'Bk_I_2', 'Bk_I_3', 'Bk_I_4',
                'Bk_II_1', 'Bk_II_2', 'Bk_II_3', 'Bk_II_4',
                'Bk_III_1', 'Bk_III_2', 'Bk_III_3', 'Bk_III_4']:
        solution[key] = model.getVarByName(key).X
    
    status_map = {gp.GRB.OPTIMAL: 'OPTIMAL', gp.GRB.INFEASIBLE: 'INFEASIBLE', 
                  gp.GRB.UNBOUNDED: 'UNBOUNDED', gp.GRB.INF_OR_UNBD: 'INF_OR_UNBD',
                  gp.GRB.TIME_LIMIT: 'TIME_LIMIT'}
    status = status_map[model.Status]
    
    return {'status': status, 'objective': model.ObjVal, 'solution': solution}