import gurobipy as gp

def build_model(data: dict) -> tuple:
    from gurobipy import GRB

    initial_fund = data["initial_fund"]
    a_ret = data["annual_project_return"]      # 1.2
    p2_ret = data["project2_return"]           # 1.5
    p3_lim = data["project3_limit"]
    p3_ret = data["project3_return"]           # 1.6
    p4_ret = data["project4_return"]           # 1.4
    p2_lim = data["project2_limit"]
    p4_lim = data["project4_limit"]

    m = gp.Model()

    # Decision variables
    x_annual_y1 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y1")
    x_annual_y2 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y2")
    x_annual_y3 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="x_annual_y3")

    x_project2_y1 = m.addVar(lb=0.0, ub=p2_lim, vtype=GRB.CONTINUOUS, name="x_project2_y1")  # 2-year project started Y1
    x_project3_y2 = m.addVar(lb=0.0, ub=p3_lim, vtype=GRB.CONTINUOUS, name="x_project3_y2")  # 2-year project started Y2
    x_project4_y3 = m.addVar(lb=0.0, ub=p4_lim, vtype=GRB.CONTINUOUS, name="x_project4_y3")  # 1-year project started Y3

    cash_after_y1 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y1")
    cash_after_y2 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y2")
    cash_after_y3 = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="cash_after_y3")

    final_amount = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="final_amount")

    m.update()

    # Cash balance equations
    m.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="cash_y1_bal")
    m.addConstr(cash_after_y2 == cash_after_y1 + a_ret * x_annual_y1 - x_annual_y2 - x_project3_y2, name="cash_y2_bal")
    m.addConstr(cash_after_y3 == cash_after_y2 + a_ret * x_annual_y2 + p2_ret * x_project2_y1 - x_annual_y3 - x_project4_y3, name="cash_y3_bal")

    # Final amount at end of year 3 includes maturities of year-3 investments and older maturities
    m.addConstr(final_amount == cash_after_y3 + a_ret * x_annual_y3 + p4_ret * x_project4_y3 + p3_ret * x_project3_y2, name="final_bal")

    # Investment feasibility across years
    m.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="year1_cap")
    m.addConstr(x_annual_y2 + x_project3_y2 <= cash_after_y1 + a_ret * x_annual_y1, name="year2_cap")
    m.addConstr(x_annual_y3 + x_project4_y3 <= cash_after_y2 + a_ret * x_annual_y2 + p2_ret * x_project2_y1, name="year3_cap")

    m.setObjective(final_amount, sense=gp.GRB.MAXIMIZE)

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
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status, str(status))

    # Fetch solution
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
        "final_amount": float(variables["final_amount"].X),
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution
    }
    return result