import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    x_annual_y1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='x_annual_y1')
    x_annual_y2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='x_annual_y2')
    x_annual_y3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='x_annual_y3')
    
    x_project2_y1 = model.addVar(lb=0, ub=data['project2_limit'], vtype=gp.GRB.CONTINUOUS, name='x_project2_y1')
    x_project3_y2 = model.addVar(lb=0, ub=data['project3_limit'], vtype=gp.GRB.CONTINUOUS, name='x_project3_y2')
    x_project4_y3 = model.addVar(lb=0, ub=data['project4_limit'], vtype=gp.GRB.CONTINUOUS, name='x_project4_y3')
    
    cash_after_y1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='cash_after_y1')
    cash_after_y2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='cash_after_y2')
    cash_after_y3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='cash_after_y3')
    
    final_amount = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name='final_amount')
    
    variables = {
        'x_annual_y1': x_annual_y1,
        'x_annual_y2': x_annual_y2,
        'x_annual_y3': x_annual_y3,
        'x_project2_y1': x_project2_y1,
        'x_project3_y2': x_project3_y2,
        'x_project4_y3': x_project4_y3,
        'cash_after_y1': cash_after_y1,
        'cash_after_y2': cash_after_y2,
        'cash_after_y3': cash_after_y3,
        'final_amount': final_amount
    }
    
    model.addConstr(data['initial_fund'] - x_annual_y1 - x_project2_y1 == cash_after_y1, name='year_1_balance')
    model.addConstr(cash_after_y1 + x_annual_y1 * data['annual_project_return'] - x_annual_y2 - x_project3_y2 == cash_after_y2, name='year_2_balance')
    model.addConstr(cash_after_y2 + x_annual_y2 * data['annual_project_return'] + x_project2_y1 * data['project2_return'] - x_annual_y3 - x_project4_y3 == cash_after_y3, name='year_3_start_balance')
    model.addConstr(cash_after_y3 + x_annual_y3 * data['annual_project_return'] + x_project3_y2 * data['project3_return'] + x_project4_y3 * data['project4_return'] == final_amount, name='final_amount_calculation')
    
    model.setObjective(final_amount, gp.GRB.MAXIMIZE)
    
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
        'x_annual_y1': variables['x_annual_y1'].X,
        'x_annual_y2': variables['x_annual_y2'].X,
        'x_annual_y3': variables['x_annual_y3'].X,
        'x_project2_y1': variables['x_project2_y1'].X,
        'x_project3_y2': variables['x_project3_y2'].X,
        'x_project4_y3': variables['x_project4_y3'].X,
        'cash_after_y1': variables['cash_after_y1'].X,
        'cash_after_y2': variables['cash_after_y2'].X,
        'cash_after_y3': variables['cash_after_y3'].X,
        'final_amount': variables['final_amount'].X
    }
    
    return {
        'status': status_map[model.Status],
        'objective': model.ObjVal,
        'solution': solution
    }