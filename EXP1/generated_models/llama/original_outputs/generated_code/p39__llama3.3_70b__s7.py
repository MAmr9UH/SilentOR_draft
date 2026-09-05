import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    start_A = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_A')
    start_B = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_B')
    start_C = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_C')
    start_D = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_D')
    start_E = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_E')
    start_F = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_F')
    start_G = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='start_G')
    
    Cmax = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='Cmax')
    machine_span = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='machine_span')

    variables = {
        "start_A": start_A,
        "start_B": start_B,
        "start_C": start_C,
        "start_D": start_D,
        "start_E": start_E,
        "start_F": start_F,
        "start_G": start_G,
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    # Precedence constraints
    for precedence in data['precedence']:
        predecessor = precedence[0]
        successor = precedence[1]
        
        if predecessor == 'A':
            model.addConstr(start_A + data['durations']['A'] <= start_G)
            if successor == 'D':
                model.addConstr(start_A + data['durations']['A'] <= start_D)
        elif predecessor == 'E':
            model.addConstr(start_E + data['durations']['E'] <= start_F)
        elif predecessor == 'G':
            model.addConstr(start_G + data['durations']['G'] <= start_F)
        elif predecessor == 'D':
            model.addConstr(start_D + data['durations']['D'] <= start_C)
        elif predecessor == 'F':
            if successor == 'C':
                model.addConstr(start_F + data['durations']['F'] <= start_C)
            elif successor == 'B':
                model.addConstr(start_F + data['durations']['F'] <= start_B)

    # Cmax constraints
    for activity in data['activities']:
        if activity == 'A':
            model.addConstr(Cmax >= start_A + data['durations']['A'])
        elif activity == 'B':
            model.addConstr(Cmax >= start_B + data['durations']['B'])
        elif activity == 'C':
            model.addConstr(Cmax >= start_C + data['durations']['C'])
        elif activity == 'D':
            model.addConstr(Cmax >= start_D + data['durations']['D'])
        elif activity == 'E':
            model.addConstr(Cmax >= start_E + data['durations']['E'])
        elif activity == 'F':
            model.addConstr(Cmax >= start_F + data['durations']['F'])
        elif activity == 'G':
            model.addConstr(Cmax >= start_G + data['durations']['G'])

    # Machine span constraint
    model.addConstr(machine_span == start_B + data['durations']['B'] - start_A)

    # Objective function
    objective = gp.quicksum([data['work_cost_per_project_day'] * Cmax, 
                             data['machine_rental_cost_per_day'] * machine_span])
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    return model, variables


def solve(data: dict) -> dict:
    model, _ = build_model(data)
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
        "start_A": model.getVarByName('start_A').X,
        "start_B": model.getVarByName('start_B').X,
        "start_C": model.getVarByName('start_C').X,
        "start_D": model.getVarByName('start_D').X,
        "start_E": model.getVarByName('start_E').X,
        "start_F": model.getVarByName('start_F').X,
        "start_G": model.getVarByName('start_G').X,
        "Cmax": model.getVarByName('Cmax').X,
        "machine_span": model.getVarByName('machine_span').X
    }

    return {
        'status': status,
        'objective': model.ObjVal,
        'solution': solution
    }