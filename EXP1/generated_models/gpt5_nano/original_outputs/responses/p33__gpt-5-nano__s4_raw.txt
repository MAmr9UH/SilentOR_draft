import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()
    
    init_fund = data["initial_fund"]
    annual_return = data["annual_project_return"]
    project2_return = data["project2_return"]
    project2_limit = data["project2_limit"]
    project3_return = data["project3_return"]
    project3_limit = data["project3_limit"]
    project4_return = data["project4_return"]
    project4_limit = data["project4_limit"]

    x_annual_y1 = m.addVar(lb=0, name="x_annual_y1")
    x_annual_y2 = m.addVar(lb=0, name="x_annual_y2")
    x_annual_y3 = m.addVar(lb=0, name="x_annual_y3")

    x_project2_y1 = m.addVar(lb=0, ub=project2_limit, name="x_project2_y1")
    x_project3_y2 = m.addVar(lb=0, ub=project3_limit, name="x_project3_y2")
    x_project4_y3 = m.addVar(lb=0, ub=project4_limit, name="x_project4_y3")

    cash_after_y1 = m.addVar(lb=0, name="cash_after_y1")
    cash_after_y2 = m.addVar(lb=0, name="cash_after_y2")
    cash_after_y3 = m.addVar(lb=0, name="cash_after_y3")

    final_amount = m.addVar(lb=0, name="final_amount")

    # Constraints
    m.addConstr(x_annual_y1 + x_project2_y1 <= init_fund)
    m.addConstr(cash_after_y1 == init_fund - x_project2_y1 + (annual_return - 1.0) * x_annual_y1)

    m.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1)
    m.addConstr(cash_after_y2 == cash_after_y1 - x_project3_y2 + (annual_return - 1.0) * x_annual_y2 + project2_return * x_project2_y1)

    m.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2)
    m.addConstr(cash_after_y3 == cash_after_y2 - x_project4_y3 + (annual_return - 1.0) * x_annual_y3 + (project4_return - 1.0) * x_project4_y3)

    m.addConstr(final_amount == cash_after_y3)

    m.setObjective(final_amount, GRB.MAXIMIZE)

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

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    model.update()
    objective_val = float(model.ObjVal)

    solution_values = {
        "x_annual_y1": float(variables["x_annual_y1"].X),
        "x_annual_y2": float(variables["x_annual_y2"].X),
        "x_annual_y3": float(variables["x_annual_y3"].X),
        "x_project2_y1": float(variables["x_project2_y1"].X),
        "x_project3_y2": float(variables["x_project3_y2"].X),
        "x_project4_y3": float(variables["x_project4_y3"].X),
        "cash_after_y1": float(variables["cash_after_y1"].X),
        "cash_after_y2": float(variables["cash_after_y2"].X),
        "cash_after_y3": float(variables["cash_after_y3"].X),
        "final_amount": float(variables["final_amount"].X)
    }

    result = {
        "status": status_str,
        "objective": objective_val,
        "solution": solution_values
    }

    return result