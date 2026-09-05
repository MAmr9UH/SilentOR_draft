import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    y1_A = model.addVar(vtype=gp.GRB.BINARY, name='y1_A')
    y1_B = model.addVar(vtype=gp.GRB.BINARY, name='y1_B')
    y2_A = model.addVar(vtype=gp.GRB.BINARY, name='y2_A')
    y2_B = model.addVar(vtype=gp.GRB.BINARY, name='y2_B')
    y3_A = model.addVar(vtype=gp.GRB.BINARY, name='y3_A')
    y3_B = model.addVar(vtype=gp.GRB.BINARY, name='y3_B')
    
    skilled_t1_A = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='skilled_t1_A')
    skilled_t1_B = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='skilled_t1_B')
    skilled_t2_A = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='skilled_t2_A')
    skilled_t3_B = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='skilled_t3_B')
    
    labor_t1_B = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='labor_t1_B')
    labor_t2_B = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='labor_t2_B')
    labor_t3_A = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='labor_t3_A')
    labor_t3_B = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='labor_t3_B')
    
    total_skilled = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='total_skilled')
    total_labor = model.addVar(lb=0, vtype=gp.GRB.INTEGER, name='total_labor')
    
    variables = {
        "y1_A": y1_A,
        "y1_B": y1_B,
        "y2_A": y2_A,
        "y2_B": y2_B,
        "y3_A": y3_A,
        "y3_B": y3_B,
        "skilled_t1_A": skilled_t1_A,
        "skilled_t1_B": skilled_t1_B,
        "skilled_t2_A": skilled_t2_A,
        "skilled_t3_B": skilled_t3_B,
        "labor_t1_B": labor_t1_B,
        "labor_t2_B": labor_t2_B,
        "labor_t3_A": labor_t3_A,
        "labor_t3_B": labor_t3_B,
        "total_skilled": total_skilled,
        "total_labor": total_labor
    }
    
    model.addConstr(y1_A + y1_B == 1, name='task_1_method_choice')
    model.addConstr(y2_A + y2_B == 1, name='task_2_method_choice')
    model.addConstr(y3_A + y3_B == 1, name='task_3_method_choice')
    
    model.addConstr(skilled_t1_A * data['weekly_effective_hours']['skilled'] >= data['task_effective_hours']['1'], name='task_1_skilled_hours')
    model.addConstr((skilled_t1_B + labor_t1_B / 2) * data['weekly_effective_hours']['labor'] >= data['task_effective_hours']['1'], name='task_1_labor_hours')
    
    model.addConstr(skilled_t2_A * data['weekly_effective_hours']['skilled'] >= data['task_effective_hours']['2'], name='task_2_skilled_hours')
    model.addConstr(labor_t2_B * data['weekly_effective_hours']['labor'] >= data['task_effective_hours']['2'], name='task_2_labor_hours')
    
    model.addConstr((skilled_t3_B + labor_t3_B / 5) * data['weekly_effective_hours']['labor'] >= data['task_effective_hours']['3'], name='task_3_mixed_hours')
    model.addConstr(labor_t3_A * data['weekly_effective_hours']['labor'] >= data['task_effective_hours']['3'], name='task_3_labor_hours')
    
    model.addConstr(total_skilled == skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B, name='total_skilled_workers')
    model.addConstr(total_labor == labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B, name='total_labor_workers')
    
    model.addConstr(total_skilled <= data['max_skilled'], name='max_skilled_workers')
    model.addConstr(total_labor <= data['max_labor'], name='max_labor_workers')
    
    model.addConstr(y1_B + y3_A <= 1, name='exclusion_constraint')
    model.addConstr(skilled_t3_B >= 20 * y3_B, name='minimum_skilled_if_task_3_B')
    
    model.addConstr(total_skilled <= data['skilled_to_labor_ratio_max'] * total_labor, name='skilled_to_labor_ratio')
    
    objective = gp.quicksum([data['weekly_wage']['skilled'] * (skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B),
                             data['weekly_wage']['labor'] * (labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B),
                             y1_B * data['method_worker_requirements']['task1_B']['fixed_setup_cost']])
    
    model.setObjective(objective, gp.GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
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
        "y1_A": variables['y1_A'].X,
        "y1_B": variables['y1_B'].X,
        "y2_A": variables['y2_A'].X,
        "y2_B": variables['y2_B'].X,
        "y3_A": variables['y3_A'].X,
        "y3_B": variables['y3_B'].X,
        "skilled_t1_A": variables['skilled_t1_A'].X,
        "skilled_t1_B": variables['skilled_t1_B'].X,
        "skilled_t2_A": variables['skilled_t2_A'].X,
        "skilled_t3_B": variables['skilled_t3_B'].X,
        "labor_t1_B": variables['labor_t1_B'].X,
        "labor_t2_B": variables['labor_t2_B'].X,
        "labor_t3_A": variables['labor_t3_A'].X,
        "labor_t3_B": variables['labor_t3_B'].X,
        "total_skilled": variables['total_skilled'].X,
        "total_labor": variables['total_labor'].X
    }
    
    return {
        'status': status,
        'objective': model.ObjVal,
        'solution': solution
    }