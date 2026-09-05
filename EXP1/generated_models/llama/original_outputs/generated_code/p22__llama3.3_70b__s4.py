import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {}

    # Create decision variable z (bottleneck bandwidth)
    variables['z'] = model.addVar(lb=0, ub=data['big_m'], vtype=gp.GRB.CONTINUOUS)

    # Create binary decision variables x_<from>_<to>
    for from_node in data['nodes']:
        for to_node in data['nodes']:
            if from_node != to_node and data['bandwidth'][from_node][to_node] > 0:
                var_name = f'x_{from_node}_{to_node}'
                variables[var_name] = model.addVar(vtype=gp.GRB.BINARY)

    # Objective: maximize bottleneck bandwidth
    model.setObjective(variables['z'], gp.GRB.MAXIMIZE)

    # Constraints: flow conservation at each node
    for node in data['nodes']:
        if node == data['source']:
            model.addConstr(gp.quicksum([variables[f'x_{node}_{to_node}'] for to_node in data['nodes'] if f'x_{node}_{to_node}' in variables]) - gp.quicksum([variables[f'x_{from_node}_{node}'] for from_node in data['nodes'] if f'x_{from_node}_{node}' in variables]) == 1)
        elif node == data['sink']:
            model.addConstr(gp.quicksum([variables[f'x_{from_node}_{node}'] for from_node in data['nodes'] if f'x_{from_node}_{node}' in variables]) - gp.quicksum([variables[f'x_{node}_{to_node}'] for to_node in data['nodes'] if f'x_{node}_{to_node}' in variables]) == 1)
        elif node == data['required_service_node']:
            model.addConstr(gp.quicksum([variables[f'x_{from_node}_{node}'] for from_node in data['nodes'] if f'x_{from_node}_{node}' in variables]) - gp.quicksum([variables[f'x_{node}_{to_node}'] for to_node in data['nodes'] if f'x_{node}_{to_node}' in variables]) == 0)
        else:
            model.addConstr(gp.quicksum([variables[f'x_{from_node}_{node}'] for from_node in data['nodes'] if f'x_{from_node}_{node}' in variables]) - gp.quicksum([variables[f'x_{node}_{to_node}'] for to_node in data['nodes'] if f'x_{node}_{to_node}' in variables]) == 0)

    # Constraints: link capacity
    for from_node in data['nodes']:
        for to_node in data['nodes']:
            if from_node != to_node and data['bandwidth'][from_node][to_node] > 0:
                var_name = f'x_{from_node}_{to_node}'
                model.addConstr(variables[var_name] * data['big_m'] >= variables['z'])

    # Constraints: link capacity (upper bound)
    for from_node in data['nodes']:
        for to_node in data['nodes']:
            if from_node != to_node and data['bandwidth'][from_node][to_node] > 0:
                var_name = f'x_{from_node}_{to_node}'
                model.addConstr(variables[var_name] * data['big_m'] <= data['bandwidth'][from_node][to_node])

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

    solution = {
        var_name: variables[var_name].X for var_name in variables
    }

    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }