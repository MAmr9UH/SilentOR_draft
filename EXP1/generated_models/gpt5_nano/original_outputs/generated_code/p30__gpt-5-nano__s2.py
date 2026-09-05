import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Parameters from data
    initial_fund = data["initial_fund"]
    annual_return = data["annual_project_return"]
    project2_return = data["project2_return"]
    project2_limit = data["project2_limit"]
    project3_return = data["project3_return"]
    project3_limit = data["project3_limit"]
    project4_return = data["project4_return"]
    project4_limit = data["project4_limit"]

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

    # Constraints modeling cash flows
    # End of year 1: cash_after_y1 = initial_fund - x_annual_y1 - x_project2_y1
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="c_y1_balance")

    # End of year 2: cash_after_y2 = cash_after_y1 + annual_return * x_annual_y1 - x_annual_y2 - x_project3_y2
    model.addConstr(cash_after_y2 == cash_after_y1 + annual_return * x_annual_y1 - x_annual_y2 - x_project3_y2, name="c_y2_balance")

    # End of year 3: final_amount will include end-year returns; constraints for final calculation
    model.addConstr(final_amount == cash_after_y3 + annual_return * x_annual_y3 + project3_return * x_project3_y2 + project4_return * x_project4_y3, name="final_amount_calc")

    # Cash available before year 3 investments
    # x_annual_y3 + x_project4_y3 <= cash_before_y3
    # cash_before_y3 = cash_after_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1, name="c_y3_balance")

    # Cash available before year 2 investments
    # x_annual_y2 + x_project3_y2 <= cash_before_y2
    # cash_before_y2 = cash_after_y1 + annual_return * x_annual_y1
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1 + annual_return * x_annual_y1, name="c_y2_balance")

    # Year 1 initial constraint: investments do not exceed initial cash
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="c_y1_limit")

    # Objective: maximize final_amount
    model.setObjective(final_amount, GRB.MAXIMIZE)

    model.update()

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

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal) if model.Status == GRB.OPTIMAL else float('nan')

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
        "final_amount": float(variables["final_amount"].X),
    }

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }