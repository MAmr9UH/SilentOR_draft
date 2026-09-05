import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("InvestmentPlan")
    model.Params.OutputFlag = 0  # silence

    initial_fund = data["initial_fund"]
    proj2_limit = data["project2_limit"]
    proj3_limit = data["project3_limit"]
    proj4_limit = data["project4_limit"]

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="final_amount")

    model.update()

    # Constraints: cash flow (year 1)
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="year1_cash")

    # Constraints: cash flow (year 2)
    # Available cash at start of year 2: initial_fund + 0.2*x_annual_y1 - x_project2_y1
    model.addConstr(x_annual_y2 + x_project3_y2 <= initial_fund + 0.2 * x_annual_y1 - x_project2_y1, name="year2_cash")

    # Constraints: cash flow (year 3)
    # Available cash at start of year 3: initial_fund + 0.2*x_annual_y1 + 0.2*x_annual_y2 - x_project3_y2 + 0.5*x_project2_y1
    model.addConstr(
        x_annual_y3 + x_project4_y3 <= initial_fund + 0.2 * x_annual_y1 + 0.2 * x_annual_y2 - x_project3_y2 + 0.5 * x_project2_y1,
        name="year3_cash"
    )

    # Investment limits
    model.addConstr(x_project2_y1 <= proj2_limit, name="limit_project2")
    model.addConstr(x_project3_y2 <= proj3_limit, name="limit_project3")
    model.addConstr(x_project4_y3 <= proj4_limit, name="limit_project4")

    # Relationships for cash_after_y1, cash_after_y2, cash_after_y3
    model.addConstr(cash_after_y1 == initial_fund - (x_annual_y1 + x_project2_y1), name="cash1_def")

    model.addConstr(
        cash_after_y2 == initial_fund + 0.2 * x_annual_y1 + 0.2 * x_annual_y2 - x_project3_y2 + 0.5 * x_project2_y1,
        name="cash2_def"
    )

    model.addConstr(
        cash_after_y3 == initial_fund
                       + 0.2 * (x_annual_y1 + x_annual_y2 + x_annual_y3)
                       + 0.5 * x_project2_y1
                       + 0.6 * x_project3_y2
                       + 0.4 * x_project4_y3,
        name="cash3_def"
    )

    # final_amount equals cash after year 3
    model.addConstr(final_amount == cash_after_y3, name="final_eq_cash3")

    # Objective: maximize final_amount
    model.setObjective(final_amount, GRB.MAXIMIZE)

    # Return model and dictionary of variables with exact keys
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

    # Status mapping
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

    objective_val = float(model.ObjVal)

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
        "objective": objective_val,
        "solution": solution
    }