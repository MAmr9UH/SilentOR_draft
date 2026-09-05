import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Data extraction
    initial_fund = data["initial_fund"]
    annual_return = data["annual_project_return"]      # e.g., 1.2
    project2_return = data["project2_return"]          # e.g., 1.5
    project2_limit = data["project2_limit"]
    project3_return = data["project3_return"]          # e.g., 1.6
    project3_limit = data["project3_limit"]
    project4_return = data["project4_return"]          # e.g., 1.4
    project4_limit = data["project4_limit"]

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0.0, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0.0, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0.0, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0.0, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0.0, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0.0, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0.0, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0.0, name="cash_after_y3")

    final_amount = model.addVar(lb=0.0, name="final_amount")

    # Objective
    model.setObjective(final_amount, GRB.MAXIMIZE)

    # Constraints

    # Year 1: start with initial fund
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="start_y1")
    model.addConstr(x_project2_y1 <= project2_limit, name="p2_cap")

    # Year 1 cash balance (uninvested cash after year 1 decisions)
    model.addConstr(cash_after_y1 == initial_fund + annual_return * x_annual_y1 - x_project2_y1, name="cash_y1_balance")

    # Year 2: investments with cash available from year 1
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="start_y2")
    model.addConstr(x_project3_y2 <= project3_limit, name="p3_cap")

    # Year 2 cash balance
    model.addConstr(cash_after_y2 == cash_after_y1 - x_annual_y2 - x_project3_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1, name="cash_y2_balance")

    # Year 3: investments with cash available from year 2
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="start_y3")
    model.addConstr(x_project4_y3 <= project4_limit, name="p4_cap")

    # End of year 3 final amount from all matured investments
    model.addConstr(final_amount == cash_after_y2 - x_annual_y3 - x_project4_y3 + annual_return * x_annual_y3 + project4_return * x_project4_y3 + project3_return * x_project3_y2, name="final_amount_calc")

    # Uninvested cash after year 3 decisions (aligned with final wealth for this horizon)
    model.addConstr(cash_after_y3 == final_amount, name="cash3_eq_final")

    # Keep references to variables for output
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

    # Status string mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))

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
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }