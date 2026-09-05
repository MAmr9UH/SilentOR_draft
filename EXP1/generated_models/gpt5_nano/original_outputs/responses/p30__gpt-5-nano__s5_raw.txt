import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("InvestmentPlan")

    initial_fund = float(data["initial_fund"])
    annual_return = float(data["annual_project_return"])  # e.g., 1.2
    project2_return = float(data["project2_return"])      # e.g., 1.5
    project2_limit = float(data["project2_limit"])        # e.g., 150000
    project3_return = float(data["project3_return"])      # e.g., 1.6
    project3_limit = float(data["project3_limit"])        # e.g., 200000
    project4_return = float(data["project4_return"])      # e.g., 1.4
    project4_limit = float(data["project4_limit"])        # e.g., 100000

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0.0, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0.0, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0.0, ub=project2_limit, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0.0, ub=project3_limit, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0.0, ub=project4_limit, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0.0, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0.0, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0.0, name="cash_after_y3")

    final_amount = model.addVar(lb=0.0, name="final_amount")

    # Objective
    model.setObjective(final_amount, GRB.MAXIMIZE)

    # Constraints
    # 1) Year 1 budget
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="start_y1")

    # 2) Year 1 cash balance at end of year1
    annual_profit_factor = annual_return - 1.0  # e.g., 0.2
    model.addConstr(cash_after_y1 == initial_fund - x_project2_y1 + annual_profit_factor * x_annual_y1, name="cash_y1_def")

    # 3) Year 2 budget
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="start_y2")

    # 4) Year 2 cash balance at end of year2
    model.addConstr(cash_after_y2 == cash_after_y1 - x_project3_y2 + annual_profit_factor * x_annual_y2 + project2_return * x_project2_y1, name="cash_y2_def")

    # 5) Year 3 budget
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="start_y3")

    # 6) Year 3 cash balance at end of year3
    model.addConstr(cash_after_y3 == cash_after_y2 - x_project4_y3 + annual_profit_factor * x_annual_y3 + project3_return * x_project3_y2, name="cash_y3_def")

    # 7) final_amount equals cash after year3
    model.addConstr(final_amount == cash_after_y3, name="final_eq")

    # Store variables in a dict with exact keys requested
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

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))
    objective_value = model.ObjVal

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
        "status": status,
        "objective": objective_value,
        "solution": solution
    }