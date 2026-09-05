import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    container_ids = data['container_ids']
    goods = data['goods']
    quantity = data['quantity']
    weight_tons = data['weight_tons']
    container_capacity_tons = data['container_capacity_tons']
    minimum_load_tons_if_used = data['minimum_load_tons_if_used']
    minimum_D_units_if_used = data['minimum_D_units_if_used']
    
    variables = {}
    
    for i in container_ids:
        variables[f'y_{i}'] = model.addVar(vtype=gp.GRB.BINARY, name=f'y_{i}')
        variables[f'uA_{i}'] = model.addVar(vtype=gp.GRB.BINARY, name=f'uA_{i}')
        
        for good in goods:
            variables[f'q_{i}_{good}'] = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f'q_{i}_{good}')
    
    # Objective: minimize the number of used containers
    model.setObjective(gp.quicksum(variables[f'y_{i}'] for i in container_ids), gp.GRB.MINIMIZE)
    
    # Constraints:
    # Each good is packed exactly once
    for good in goods:
        model.addConstr(gp.quicksum(variables[f'q_{i}_{good}'] for i in container_ids) == quantity[good], name=f'pack_all_{good}')
    
    # Container capacity constraints
    for i in container_ids:
        model.addConstr(
            gp.quicksum(weight_tons[good] * variables[f'q_{i}_{good}'] for good in goods) <= container_capacity_tons * variables[f'y_{i}'],
            name=f'capacity_{i}'
        )
        
        # Minimum load constraint if the container is used
        model.addConstr(
            gp.quicksum(weight_tons[good] * variables[f'q_{i}_{good}'] for good in goods) >= minimum_load_tons_if_used * variables[f'y_{i}'],
            name=f'minimum_load_{i}'
        )
        
        # Minimum D units constraint if the container is used
        model.addConstr(
            variables[f'q_{i}_D'] >= minimum_D_units_if_used * variables[f'y_{i}'],
            name=f'minimum_D_{i}'
        )
    
    # A requires at least one C in the same container
    for i in container_ids:
        model.addConstr(variables[f'uA_{i}'] <= variables[f'q_{i}_C'], name=f'A_requires_C_{i}')
        
        # If any A is packed, then uA must be 1
        model.addConstr(variables[f'uA_{i}'] >= variables[f'q_{i}_A'], name=f'uA_if_A_{i}')
    
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
    
    solution = {var_key: variables[var_key].X for var_key in variables}
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }