import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Data
    initial_fund = data["initial_fund"]
    ret1 = data["annual_project_return"]  # e.g., 1.2
    ret2 = data["project2_return"]       # e.g., 1.5
    ret3 = data["project3_return"]       # e.g., 1.6
    ret4 = data["project4_return"]       # e.g., 1.4

    proj2_lim = data["project2_limit"]
    proj3_lim = data["project3_limit"]
    proj4_lim = data["project4_limit"]

    # Decision variables
    x_annual_y1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y1")      # Year 1: one-year product
    x_project2_y1 = model.addVar(lb=0, ub=proj2_lim, vtype=GRB.CONTINUOUS, name="x_project2_y1")  # Year 1: 2-year product

    cash_after_y1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y1")

    x_annual_y2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y2")      # Year 2: one-year product
    x_project3_y2 = model.addVar(lb=0, ub=proj3_lim, vtype=GRB.CONTINUOUS, name="x_project3_y2")  # Year 2: same-year product

    cash_after_y2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y2")

    x_annual_y3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="x_annual_y3")      # Year 3: one-year product
    x_project4_y3 = model.addVar(lb=0, ub=proj4_lim, vtype=GRB.CONTINUOUS, name="x_project4_y3")  # Year 3: 1-year product

    cash_after_y3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="final_amount")

    # Constraints
    # Year 1 budget: investments cannot exceed initial fund
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="yr1_budget")

    # Year 1 cash balance
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1 + ret1 * x_annual_y1, name="yr1_cash_balance")
    model.addConstr(cash_after_y1 >= 0, name="yr1_cash_nonneg")

    # Year 2 budget: investments cannot exceed cash available at start of Year 2
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="yr2_budget")

    # Year 2 cash balance
    model.addConstr(
        cash_after_y2 == cash_after_y1 - x_annual_y2 - x_project3_y2
                       + ret1 * x_annual_y2 + ret3 * x_project3_y2 + ret2 * x_project2_y1,
        name="yr2_cash_balance"
    )
    model.addConstr(cash_after_y2 >= 0, name="yr2_cash_nonneg")

    # Year 3 budget: investments cannot exceed cash available at start of Year 3
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="yr3_budget")

    # Year 3 cash balance
    model.addConstr(
        cash_after_y3 == cash_after_y2 - x_annual_y3 - x_project4_y3
                       + ret1 * x_annual_y3 + ret4 * x_project4_y3,
        name="yr3_cash_balance"
    )
    model.addConstr(cash_after_y3 >= 0, name="yr3_cash_nonneg")

    # Final amount equals cash after Year 3
    model.addConstr(final_amount == cash_after_y3, name="final_eq_cash_end")

    # Objective: maximize final amount
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

    status_val = model.Status
    if status_val == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_val == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_val == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_val == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_val == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_val)

    solution = {
        key: float(var.X) for key, var in variables.items()
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution
    }

    return result