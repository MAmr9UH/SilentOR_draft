import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Read data
    initial_fund = float(data.get("initial_fund", 0.0))
    annual_return = float(data.get("annual_project_return", 1.0))
    project2_return = float(data.get("project2_return", 1.0))
    project2_limit = float(data.get("project2_limit", 0.0))
    project3_return = float(data.get("project3_return", 1.0))
    project3_limit = float(data.get("project3_limit", 0.0))
    project4_return = float(data.get("project4_return", 1.0))
    project4_limit = float(data.get("project4_limit", 0.0))
    # Years can be read if needed (not used directly)
    # years = list(data.get("years", []))

    model = gp.Model("Investment_Portfolio")

    # Decision variables
    x_annual_y1  = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2  = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3  = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="final_amount")

    # Constraints for cash flow
    # Year 1: cash_after_y1 = initial_fund - x_annual_y1 - x_project2_y1
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="eq_y1_cash")

    # Year 2: cash_after_y2 = (cash_after_y1 + annual_return * x_annual_y1) - (x_annual_y2 + x_project3_y2)
    model.addConstr(cash_after_y2 == (cash_after_y1 + annual_return * x_annual_y1) - (x_annual_y2 + x_project3_y2), name="eq_y2_cash")

    # Year 3: cash_after_y3 = (cash_after_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1) - (x_annual_y3 + x_project4_y3)
    model.addConstr(cash_after_y3 == (cash_after_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1) - (x_annual_y3 + x_project4_y3), name="eq_y3_cash")

    # Final amount at end of Year 3
    model.addConstr(final_amount == cash_after_y3 + annual_return * x_annual_y3 + project4_return * x_project4_y3, name="eq_final_amount")

    # Investment caps
    model.addConstr(x_project2_y1 <= project2_limit, name="cap_p2_y1")
    model.addConstr(x_project3_y2 <= project3_limit, name="cap_p3_y2")
    model.addConstr(x_project4_y3 <= project4_limit, name="cap_p4_y3")

    # Objective: maximize final_amount
    model.setObjective(final_amount, GRB.MAXIMIZE)

    model.update()

    # Pack variables into the required dictionary
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

    objective_value = float(model.ObjVal)

    # Extract solution
    solution_values = {}
    for key in [
        "x_annual_y1",
        "x_annual_y2",
        "x_annual_y3",
        "x_project2_y1",
        "x_project3_y2",
        "x_project4_y3",
        "cash_after_y1",
        "cash_after_y2",
        "cash_after_y3",
        "final_amount",
    ]:
        solution_values[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution_values
    }