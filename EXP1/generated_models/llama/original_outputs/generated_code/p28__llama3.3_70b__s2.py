import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for warehouse in data['warehouses']:
        for port in data['ports']:
            x_key = f'x_{warehouse}_{port}'
            t_key = f't_{warehouse}_{port}'
            
            variables[x_key] = model.addVar(vtype=gp.GRB.INTEGER, name=x_key)
            variables[t_key] = model.addVar(vtype=gp.GRB.INTEGER, name=t_key)
    
    # Objective function
    obj_expr = gp.quicksum(variables[f't_{warehouse}_{port}'] * data['distance_km'][warehouse][port] * data['cost_per_km_per_truck']
                           for warehouse in data['warehouses'] for port in data['ports'])
    model.setObjective(obj_expr, gp.GRB.MINIMIZE)
    
    # Supply constraints
    for warehouse in data['warehouses']:
        supply_expr = gp.quicksum(variables[f'x_{warehouse}_{port}'] for port in data['ports'])
        model.addConstr(supply_expr <= data['supply'][warehouse], name=f'supply_{warehouse}')
    
    # Demand constraints
    for port in data['ports']:
        demand_expr = gp.quicksum(variables[f'x_{warehouse}_{port}'] for warehouse in data['warehouses'])
        model.addConstr(demand_expr == data['demand'][port], name=f'demand_{port}')
    
    # Truck capacity constraints
    for warehouse in data['warehouses']:
        for port in data['ports']:
            truck_capacity_expr = variables[f'x_{warehouse}_{port}'] - 2 * variables[f't_{warehouse}_{port}']
            model.addConstr(truck_capacity_expr <= 0, name=f'truck_capacity_{warehouse}_{port}')
    
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
    
    solution = {key: variables[key].X for key in variables}
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }