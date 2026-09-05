import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    m = gp.Model("fund_allocation_three_years")

    initial_fund = data["initial_fund"]
    annual_return = data["annual_project_return"]
    project2_return = data["project2_return"]
    project2_limit = data["project2_limit"]
    project3_return = data["project3_return"]
    project3_limit = data["project3_limit"]
    project4_return = data["project4_return"]
    project4_limit = data["project4_limit"]

    # Decision variables
    x_annual_y1 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_project2_y1")
    x_project3_y2 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_project3_y2")
    x_project4_y3 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_project4_y3")

    cash_after_y1 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = m.addVar(lb=0, vtype=GRB.CONTINUOUS, name="final_amount")

    # Constraints for cash balances across years
    m.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="cash_y1_balance")
    m.addConstr(cash_after_y2 == cash_after_y1 + annual_return * x_annual_y1 - x_annual_y2 - x_project3_y2, name="cash_y2_balance")
    m.addConstr(cash_after_y3 == cash_after_y2 + project2_return * x_project2_y1 + annual_return * x_annual_y2 - x_annual_y3 - x_project4_y3, name="cash_y3_balance")

    # Final amount at end of year 3
    m.addConstr(final_amount == cash_after_y3 + annual_return * x_annual_y3 + project4_return * x_project4_y3 + project3_return * x_project3_y2, name="final_amount_calc")

    # Investment limits
    m.addConstr(x_annual_y1 <= initial_fund, name="limit_y1")
    m.addConstr(x_project2_y1 <= project2_limit, name="limit_project2_y1")
    m.addConstr(x_project3_y2 <= project3_limit, name="limit_project3_y2")
    m.addConstr(x_project4_y3 <= project4_limit, name="limit_project4_y3")

    # Nonnegativity of cash balances (explicit)
    m.addConstr(cash_after_y1 >= 0, name="nonneg_cash_y1")
    m.addConstr(cash_after_y2 >= 0, name="nonneg_cash_y2")
    m.addConstr(cash_after_y3 >= 0, name="nonneg_cash_y3")

    # Objective: maximize final amount
    m.setObjective(final_amount, GRB.MAXIMIZE)

    # Return model and a dict of variables with required keys
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

    model.update()
    # Status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal) if model.Status == GRB.OPTIMAL else None

    solution = {}
    for key, var in variables.items():
        # Read variable values
        val = float(var.X) if var is not None else 0.0
        solution[key] = val

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }