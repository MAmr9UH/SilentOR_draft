import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    initial_fund = float(data["initial_fund"])
    annual_return = float(data["annual_project_return"])
    project2_return = float(data["project2_return"])
    project2_limit = float(data["project2_limit"])
    project3_return = float(data["project3_return"])
    project3_limit = float(data["project3_limit"])
    project4_return = float(data["project4_return"])
    project4_limit = float(data["project4_limit"])

    # Decision variables
    x_annual_y1 = model.addVar(lb=0.0, name="x_annual_y1", vtype=gp.GRB.CONTINUOUS)
    x_annual_y2 = model.addVar(lb=0.0, name="x_annual_y2", vtype= gp.GRB.CONTINUOUS)
    x_annual_y3 = model.addVar(lb=0.0, name="x_annual_y3", vtype= gp.GRB.CONTINUOUS)

    x_project2_y1 = model.addVar(lb=0.0, ub=project2_limit, name="x_project2_y1", vtype=gp.GRB.CONTINUOUS)
    x_project3_y2 = model.addVar(lb=0.0, ub=project3_limit, name="x_project3_y2", vtype=gp.GRB.CONTINUOUS)
    x_project4_y3 = model.addVar(lb=0.0, ub=project4_limit, name="x_project4_y3", vtype=gp.GRB.CONTINUOUS)

    cash_after_y1 = model.addVar(lb=0.0, name="cash_after_y1", vtype=gp.GRB.CONTINUOUS)
    cash_after_y2 = model.addVar(lb=0.0, name="cash_after_y2", vtype=gp.GRB.CONTINUOUS)
    cash_after_y3 = model.addVar(lb=0.0, name="cash_after_y3", vtype=gp.GRB.CONTINUOUS)

    final_amount = model.addVar(lb=0.0, name="final_amount", vtype=gp.GRB.CONTINUOUS)

    # Constraints linking cash and investments
    # Year 1: invest i1 and j1, rest is cash
    model.addConstr(x_annual_y1 + x_project2_y1 <= initial_fund, name="year1_budget")

    # Year 2: available cash is initial_fund - j1 + 0.2*i1
    model.addConstr(x_annual_y2 + x_project3_y2 <= initial_fund - x_project2_y1 + annual_return * x_annual_y1, name="year2_budget")

    # Year 3: available cash is A2 - i2 - k2 + returns from i2 and k2 and j1's return
    # A3 = initial_fund + 0.2*i1 + 0.2*i2 + 0.6*k2 + 0.5*j1
    model.addConstr(
        x_annual_y3 + x_project4_y3 <=
        initial_fund + 0.2 * x_annual_y1 + 0.2 * x_annual_y2 + 0.6 * x_project3_y2 + 0.5 * x_project2_y1,
        name="year3_budget"
    )

    # Cash balance equations
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="cash_after_y1_eq")
    model.addConstr(cash_after_y2 == (initial_fund - x_project2_y1 + annual_return * x_annual_y1) - x_annual_y2 - x_project3_y2, name="cash_after_y2_eq")
    model.addConstr(cash_after_y3 == (initial_fund - x_project2_y1 + annual_return * x_annual_y1) - x_annual_y2 - x_project3_y2  \
                    + annual_return * x_annual_y2 + project3_return * x_project3_y2 - x_annual_y3 - x_project4_y3, name="cash_after_y3_eq")
    # The above cash_after_y3_eq simplifies to an equivalent that ensures consistency; keep as is to reflect cash flow explicitly.

    # Final amount at end of year 3
    model.addConstr(final_amount == cash_after_y3 \
                    + annual_return * x_annual_y3 + project4_return * x_project4_y3, name="final_amount_eq")

    # Objective: maximize final_amount
    model.setObjective(final_amount, sense=gp.GRB.MAXIMIZE)

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
    status_code = model.Status

    status_str = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }.get(status_code, str(status_code))

    # Update to ensure values are current
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

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }