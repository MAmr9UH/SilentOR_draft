import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    variables = {}
    
    for warehouse in data['warehouses']:
        for port in data['ports']:
            x_key = f'x_{warehouse}_{port}'
            t_key = f't_{warehouse}_{port}'
            
            variables[x_key] = model.addVar(lb=0, ub=data['supply'][warehouse], vtype=gp.GRB.INTEGER)
            variables[t_key] = model.addVar(lb=0, vtype=gp.GRB.INTEGER)
    
    for warehouse in data['warehouses']:
        supply_constr = gp.quicksum(variables[f'x_{warehouse}_{port}'] for port in data['ports'])
        model.addConstr(supply_constr <= data['supply'][warehouse])
        
    for port in data['ports']:
        demand_constr = gp.quicksum(variables[f'x_{warehouse}_{port}'] for warehouse in data['warehouses'])
        model.addConstr(demand_constr == data['demand'][port])
        
    for warehouse in data['warehouses']:
        for port in data['ports']:
            x_key = f'x_{warehouse}_{port}'
            t_key = f't_{warehouse}_{port}'
            
            truck_capacity_constr = gp.quicksum(variables[x_key]) / data['truck_capacity_containers'] - variables[t_key]
            model.addConstr(truck_capacity_constr <= 0)
    
    objective = gp.quicksum(data['distance_km'][warehouse][port] * data['cost_per_km_per_truck'] * variables[f't_{warehouse}_{port}'] for warehouse in data['warehouses'] for port in data['ports'])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: 'OPTIMAL',
        gp.GRB.INFEASIBLE: 'INFEASIBLE',
        gp.GRB.UNBOUNDED: 'UNBOUNDED',
        gp.GRB.INF_OR_UNBD: 'INF_OR_UNBD',
        gp.GRB.TIME_LIMIT: 'TIME_LIMIT'
    }
    
    solution = {}
    for warehouse in data['warehouses']:
        for port in data['ports']:
            x_key = f'x_{warehouse}_{port}'
            t_key = f't_{warehouse}_{port}'
            
            solution[x_key] = model.getVarByName(x_key).X
            solution[t_key] = model.getVarByName(t_key).X
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }