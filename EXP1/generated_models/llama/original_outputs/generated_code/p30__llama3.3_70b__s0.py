import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    x_annual_y1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    x_annual_y2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    x_annual_y3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    x_project2_y1 = model.addVar(lb=0, ub=data["project2_limit"], vtype=gp.GRB.CONTINUOUS)
    x_project3_y2 = model.addVar(lb=0, ub=data["project3_limit"], vtype=gp.GRB.CONTINUOUS)
    x_project4_y3 = model.addVar(lb=0, ub=data["project4_limit"], vtype=gp.GRB.CONTINUOUS)
    
    cash_after_y1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    cash_after_y2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    cash_after_y3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    final_amount = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    variables = {
        "x_annual_y1": x_annual_y1,
        "x_annual_y2": x_annual_y2,
        "x_annual_y3": x_annual_y3,
        "x_project2_y1": x_project2_y1,
        "x_project3_y2": x_project3_y2,
        "x_project4_y3": x_project4_y3,
        "cash_after_y1": cash_after_y1,
        "cash_after_y2": cash_after_y2,
        "cash_after_y3": cash_after_y3,
        "final_amount": final_amount
    }
    
    model.addConstr(data["initial_fund"] - x_annual_y1 - x_project2_y1 == cash_after_y1)
    model.addConstr(cash_after_y1 + data["annual_project_return"] * x_annual_y1 - x_annual_y2 - x_project3_y2 == cash_after_y2)
    model.addConstr(cash_after_y2 + data["project2_return"] * x_project2_y1 + data["annual_project_return"] * x_annual_y2 - x_annual_y3 - x_project4_y3 == cash_after_y3)
    
    model.addConstr(final_amount == cash_after_y3 + data["project3_return"] * x_project3_y2 + data["annual_project_return"] * x_annual_y3 + data["project4_return"] * x_project4_y3)
    
    model.setObjective(final_amount, gp.GRB.MAXIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {
        "x_annual_y1": variables["x_annual_y1"].X,
        "x_annual_y2": variables["x_annual_y2"].X,
        "x_annual_y3": variables["x_annual_y3"].X,
        "x_project2_y1": variables["x_project2_y1"].X,
        "x_project3_y2": variables["x_project3_y2"].X,
        "x_project4_y3": variables["x_project4_y3"].X,
        "cash_after_y1": variables["cash_after_y1"].X,
        "cash_after_y2": variables["cash_after_y2"].X,
        "cash_after_y3": variables["cash_after_y3"].X,
        "final_amount": variables["final_amount"].X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }