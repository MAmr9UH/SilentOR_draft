import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    # Data parameters (read from input)
    initial_fund = float(data.get("initial_fund", 0.0))
    annual_return = float(data.get("annual_project_return", 1.0))  # e.g., 1.2
    project2_return = float(data.get("project2_return", 1.0))     # e.g., 1.5
    project2_limit = float(data.get("project2_limit", 0.0))
    project3_return = float(data.get("project3_return", 1.0))     # e.g., 1.6
    project3_limit = float(data.get("project3_limit", 0.0))
    project4_return = float(data.get("project4_return", 1.0))     # e.g., 1.4
    project4_limit = float(data.get("project4_limit", 0.0))

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

    # Constraints
    # Year 1 investment feasibility and per-project limits
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="year1_invest_cap")
    model.addConstr(x_project2_y1 <= project2_limit, name="year1_project2_lim")

    # Year 2 investment feasibility and per-project limits
    model.addConstr(x_project3_y2 <= project3_limit, name="year2_project3_lim")

    # Year 3 investment feasibility and per-project limits
    model.addConstr(x_project4_y3 <= project4_limit, name="year3_project4_lim")

    # Cash flow constraints
    model.addConstr(cash_after_y1 == initial_fund + 0.2 * x_annual_y1 - x_project2_y1, name="cash_after_y1_calc")
    model.addConstr(cash_after_y2 == cash_after_y1 + 0.2 * x_annual_y2 - x_project3_y2 + 1.5 * x_project2_y1, name="cash_after_y2_calc")
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="year3_invest_cap")
    model.addConstr(final_amount == cash_after_y2 + 0.2 * x_annual_y3 + 0.4 * x_project4_y3 + 1.6 * x_project3_y2, name="final_amount_calc")
    model.addConstr(cash_after_y3 == final_amount, name="cash_after_y3_equals_final")

    # Objective: maximize final amount at end of year 3
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

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    objective_val = float(model.ObjVal) if model.ObjVal is not None else 0.0

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