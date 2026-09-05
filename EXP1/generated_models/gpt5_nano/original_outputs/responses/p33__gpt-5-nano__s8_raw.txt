import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    initial_fund = data.get("initial_fund", 0.0)
    project2_limit = data.get("project2_limit", 0.0)
    project3_limit = data.get("project3_limit", 0.0)
    project4_limit = data.get("project4_limit", 0.0)

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0.0, ub=project2_limit, vtype=GRB.CONTINUOUS, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0.0, ub=project3_limit, vtype=GRB.CONTINUOUS, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0.0, ub=project4_limit, vtype=GRB.CONTINUOUS, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y3")
    final_amount = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="final_amount")

    model.update()

    # Constraints
    # Year 1: investment limits
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="yr1_invest_limit")

    # Year 1 cash after investments
    model.addConstr(cash_after_y1 == initial_fund - x_project2_y1 + 0.2 * x_annual_y1, name="cash_after_y1_express")

    # Year 2: investment limits
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="yr2_invest_limit")

    # Year 2 cash after investments
    model.addConstr(
        cash_after_y2 == cash_after_y1 - x_annual_y2 - x_project3_y2
        + 1.2 * x_annual_y2 + 1.6 * x_project3_y2 + 1.5 * x_project2_y1,
        name="cash_after_y2_express"
    )

    # Year 3: investment limits
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="yr3_invest_limit")

    # Year 3 cash after investments
    model.addConstr(cash_after_y3 == cash_after_y2 - x_annual_y3 - x_project4_y3, name="cash_after_y3_express")

    # Final amount at end of Year 3
    model.addConstr(final_amount == cash_after_y3 + 1.2 * x_annual_y3 + 1.4 * x_project4_y3, name="final_amount_calc")

    # Objective: maximize final_amount
    model.setObjective(final_amount, GRB.MAXIMIZE)

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

    objective_value = float(model.ObjVal)

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
        "objective": objective_value,
        "solution": solution
    }