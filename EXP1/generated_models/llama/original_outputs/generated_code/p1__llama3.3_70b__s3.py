import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    produced = {str(i+1): model.addVar(vtype=gp.GRB.INTEGER, name=f'produced_{i+1}') for i in range(len(data['cap']))}
    allocation = {(str(i+1), str(j+1)): model.addVar(vtype=gp.GRB.INTEGER, name=f'allocation_{i+1}_{j+1}') 
                  for i in range(len(data['cap'])) for j in range(len(data['cap'])) if data['cap'][i] >= data['cap'][j]}
    
    variables = {'produced': produced, 'allocation': allocation}
    
    # Objective function
    model.setObjective(gp.quicksum([data['vcost'][i]*produced[str(i+1)] for i in range(len(data['cap']))]) + 
                       gp.quicksum([data['fixed']*(produced[str(i+1)] > 0) for i in range(len(data['cap']))]))
    
    # Constraints
    for j in range(len(data['cap'])):
        model.addConstr(gp.quicksum([allocation.get((str(i+1), str(j+1)), 0) for i in range(len(data['cap'])) if data['cap'][i] >= data['cap'][j]]) == data['dem'][j])
    
    for i in range(len(data['cap'])):
        model.addConstr(produced[str(i+1)] >= gp.quicksum([allocation.get((str(i+1), str(j+1)), 0) for j in range(len(data['cap'])) if data['cap'][i] >= data['cap'][j]]))
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    solution = {
        'produced': {key: var.X for key, var in variables['produced'].items()},
        'allocation': {key: var.X for key, var in variables['allocation'].items()}
    }
    
    result = {
        'status': None,
        'objective': model.ObjVal,
        'solution': solution
    }
    
    if model.Status == gp.GRB.OPTIMAL:
        result['status'] = 'OPTIMAL'
    elif model.Status == gp.GRB.INFEASIBLE:
        result['status'] = 'INFEASIBLE'
    elif model.Status == gp.GRB.UNBOUNDED:
        result['status'] = 'UNBOUNDED'
    elif model.Status == gp.GRB.INF_OR_UNBD:
        result['status'] = 'INF_OR_UNBD'
    elif model.Status == gp.GRB.TIME_LIMIT:
        result['status'] = 'TIME_LIMIT'
    
    return result