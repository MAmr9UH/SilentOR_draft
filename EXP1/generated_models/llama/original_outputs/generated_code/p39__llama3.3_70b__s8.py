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

    for precedence in data['precedence']:
        if precedence[0] == 'A':
            model.addConstr(start_A + data['durations']['A'] <= start_D, name='A_to_D')
            model.addConstr(start_A + data['durations']['A'] <= start_G, name='A_to_G')
        elif precedence[0] == 'E':
            model.addConstr(start_E + data['durations']['E'] <= start_F, name='E_to_F')
        elif precedence[0] == 'G':
            model.addConstr(start_G + data['durations']['G'] <= start_F, name='G_to_F')
        elif precedence[0] == 'D':
            model.addConstr(start_D + data['durations']['D'] <= start_C, name='D_to_C')
        elif precedence[0] == 'F':
            if precedence[1] == 'C':
                model.addConstr(start_F + data['durations']['F'] <= start_C + data['durations']['C'], name='F_to_C')
            else:
                model.addConstr(start_F + data['durations']['F'] <= start_B, name='F_to_B')

    for activity in data['activities']:
        if activity == 'A':
            continue
        elif activity == 'B':
            model.addConstr(start_B + data['durations']['B'] <= Cmax, name='B_to_Cmax')
        else:
            model.addConstr(start_A + data['durations']['A'] <= start_G + data['durations']['G'], name='A_to_G_duration')
            if activity == 'C':
                model.addConstr(start_C + data['durations']['C'] <= Cmax, name='C_to_Cmax')
            elif activity == 'D':
                continue
            elif activity == 'E':
                model.addConstr(start_E + data['durations']['E'] <= Cmax, name='E_to_Cmax')
            elif activity == 'F':
                model.addConstr(start_F + data['durations']['F'] <= Cmax, name='F_to_Cmax')
            elif activity == 'G':
                continue

    model.addConstr(machine_span == start_B + data['durations']['B'] - start_A, name='machine_span')

    objective = gp.quicksum([data['work_cost_per_project_day'] * Cmax]) + gp.quicksum([data['machine_rental_cost_per_day'] * machine_span])
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