import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    variables = {}
    
    # Create decision variable z (bottleneck bandwidth)
    variables['z'] = model.addVar(lb=0, ub=data['big_m'], vtype=gp.GRB.CONTINUOUS, name='z')
    
    # Create binary decision variables x_<from>_<to>
    for from_node in data['nodes']:
        for to_node in data['nodes']:
            if from_node != to_node and data['bandwidth'][from_node][to_node] > 0:
                var_name = f'x_{from_node}_{to_node}'
                variables[var_name] = model.addVar(vtype=gp.GRB.BINARY, name=var_name)
    
    # Objective: maximize bottleneck bandwidth
    model.setObjective(variables['z'], gp.GRB.MAXIMIZE)
    
    # Constraints:
    # 1. Flow conservation at each node (except source and sink)
    for node in data['nodes']:
        if node != data['source'] and node != data['sink']:
            flow_in = gp.quicksum([variables[f'x_{from_node}_{node}'] for from_node in data['nodes'] if from_node != node and data['bandwidth'][from_node][node] > 0])
            flow_out = gp.quicksum([variables[f'x_{node}_{to_node}'] for to_node in data['nodes'] if to_node != node and data['bandwidth'][node][to_node] > 0])
            model.addConstr(flow_in == flow_out, f'flow_conservation_{node}')
    
    # 2. Flow conservation at source node
    flow_out_source = gp.quicksum([variables[f'x_{data["source"]}_{to_node}'] for to_node in data['nodes'] if to_node != data['source'] and data['bandwidth'][data['source']][to_node] > 0])
    model.addConstr(flow_out_source == 1, f'flow_conservation_source')
    
    # 3. Flow conservation at sink node
    flow_in_sink = gp.quicksum([variables[f'x_{from_node}_{data["sink"]}'] for from_node in data['nodes'] if from_node != data['sink'] and data['bandwidth'][from_node][data['sink']] > 0])
    model.addConstr(flow_in_sink == 1, f'flow_conservation_sink')
    
    # 4. Required service node constraint
    flow_through_service_node = gp.quicksum([variables[f'x_{from_node}_{data["required_service_node"]}'] for from_node in data['nodes'] if from_node != data['required_service_node'] and data['bandwidth'][from_node][data['required_service_node']] > 0])
    model.addConstr(flow_through_service_node == 1, f'required_service_node')
    
    # 5. Bandwidth constraints
    for from_node in data['nodes']:
        for to_node in data['nodes']:
            if from_node != to_node and data['bandwidth'][from_node][to_node] > 0:
                var_name = f'x_{from_node}_{to_node}'
                model.addConstr(variables[var_name] * data['big_m'] >= variables['z'], f'bandwidth_constraint_{var_name}')
                model.addConstr(data['bandwidth'][from_node][to_node] * variables[var_name] >= variables['z'], f'bandwidth_constraint_{var_name}_2')
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    solution = {}
    for var in variables:
        solution[var] = variables[var].X
    
    status_map = {
        gp.GRB.OPTIMAL: 'OPTIMAL',
        gp.GRB.INFEASIBLE: 'INFEASIBLE',
        gp.GRB.UNBOUNDED: 'UNBOUNDED',
        gp.GRB.INF_OR_UNBD: 'INF_OR_UNBD',
        gp.GRB.TIME_LIMIT: 'TIME_LIMIT'
    }
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }