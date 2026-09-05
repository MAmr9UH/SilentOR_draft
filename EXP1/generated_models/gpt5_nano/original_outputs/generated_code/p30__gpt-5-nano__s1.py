import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Read instance data
    initial_fund = data["initial_fund"]
    annual_return = data["annual_project_return"]
    project2_return = data["project2_return"]
    project2_limit = data["project2_limit"]
    project3_return = data["project3_return"]
    project3_limit = data["project3_limit"]
    project4_return = data["project4_return"]
    project4_limit = data["project4_limit"]

    # Decision variables
    x_annual_y1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0, ub=project2_limit, vtype=GRB.CONTINUOUS, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0, ub=project3_limit, vtype=GRB.CONTINUOUS, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0, ub=project4_limit, vtype=GRB.CONTINUOUS, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="final_amount")

    # Constraints for cash balance across years
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1 + annual_return * x_annual_y1, name="cash_y1_balance")
    model.addConstr(cash_after_y2 == cash_after_y1 - x_annual_y2 - x_project3_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1, name="cash_y2_balance")
    model.addConstr(cash_after_y3 == cash_after_y2 - x_annual_y3 - x_project4_y3 + annual_return * x_annual_y3 + project3_return * x_project3_y2 + project4_return * x_project4_y3, name="cash_y3_balance")
    model.addConstr(final_amount == cash_after_y3, name="final_amount_balance")

    # Capacity constraints per year
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="year1_cap")
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="year2_cap")
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="year3_cap")

    # Objective: maximize final amount
    model.setObjective(final_amount, GRB.MAXIMIZE)

    # Prepare variables dictionary to return
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

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Read status and objective
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    model.update()

    solution = {
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

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }