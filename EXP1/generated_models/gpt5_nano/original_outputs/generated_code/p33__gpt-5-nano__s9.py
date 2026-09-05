import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    initial_fund = data["initial_fund"]
    r1 = data["annual_project_return"]  # 1-year project return factor
    rb2 = data["project2_return"]       # 2-year project return factor
    cap2 = data["project2_limit"]
    r3 = data["project3_return"]        # 2-year same-year project return factor
    cap3 = data["project3_limit"]
    r4 = data["project4_return"]        # 1-year year3 project return factor
    cap4 = data["project4_limit"]

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, name="x_annual_y1", vtype=GRB.CONTINUOUS)
    x_annual_y2 = model.addVar(lb=0.0, name="x_annual_y2", vtype=GRB.CONTINUOUS)
    x_annual_y3 = model.addVar(lb=0.0, name="x_annual_y3", vtype=GRB.CONTINUOUS)

    x_project2_y1 = model.addVar(lb=0.0, ub=cap2, name="x_project2_y1", vtype=GRB.CONTINUOUS)
    x_project3_y2 = model.addVar(lb=0.0, ub=cap3, name="x_project3_y2", vtype=GRB.CONTINUOUS)
    x_project4_y3 = model.addVar(lb=0.0, ub=cap4, name="x_project4_y3", vtype=GRB.CONTINUOUS)

    cash_after_y1 = model.addVar(lb=0.0, name="cash_after_y1", vtype=GRB.CONTINUOUS)
    cash_after_y2 = model.addVar(lb=0.0, name="cash_after_y2", vtype=GRB.CONTINUOUS)
    cash_after_y3 = model.addVar(lb=0.0, name="cash_after_y3", vtype=GRB.CONTINUOUS)

    final_amount = model.addVar(lb=0.0, name="final_amount", vtype=GRB.CONTINUOUS)

    model.update()

    # Constraints and recurrences

    # Year 1: Invest up to initial fund
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="yr1_invest_cap")

    # Cash flow recurrences
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1 + r1 * x_annual_y1,
                    name="cash_after_y1_eq")

    # Year 2: Investments cannot exceed cash available after Year 1
    model.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1, name="yr2_invest_cap")

    # Cash after Year 2
    model.addConstr(
        cash_after_y2 == cash_after_y1 - x_annual_y2 - x_project3_y2 + r1 * x_annual_y2 + r3 * x_project3_y2 + rb2 * x_project2_y1,
        name="cash_after_y2_eq"
    )

    # Year 3: Investments cannot exceed cash available after Year 2
    model.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2, name="yr3_invest_cap")

    # Cash after Year 3 (before final payout)
    model.addConstr(cash_after_y3 == cash_after_y2 - x_annual_y3 - x_project4_y3, name="cash_after_y3_eq")

    # Final amount after Year 3 (including payouts from Year 3 investments)
    model.addConstr(final_amount == cash_after_y3 + r1 * x_annual_y3 + r4 * x_project4_y3, name="final_amount_calc")

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

def _status_to_string(status_code) -> str:
    if status_code == GRB.OPTIMAL:
        return "OPTIMAL"
    if status_code == GRB.INFEASIBLE:
        return "INFEASIBLE"
    if status_code == GRB.UNBOUNDED:
        return "UNBOUNDED"
    if status_code == GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if status_code == GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    return str(status_code)

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_str = _status_to_string(model.Status)

    # Ensure values are up-to-date
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

    result = {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result