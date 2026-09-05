import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Data extraction
    initial_fund = data.get("initial_fund", 0.0)
    annual_return = data.get("annual_project_return", 1.0)
    project2_return = data.get("project2_return", 1.0)
    project2_limit = data.get("project2_limit", None)
    project3_return = data.get("project3_return", 1.0)
    project3_limit = data.get("project3_limit", None)
    project4_return = data.get("project4_return", 1.0)
    project4_limit = data.get("project4_limit", None)

    # Decision variables
    x_annual_y1 = model.addVar(lb=0, name="x_annual_y1")
    x_annual_y2 = model.addVar(lb=0, name="x_annual_y2")
    x_annual_y3 = model.addVar(lb=0, name="x_annual_y3")

    x_project2_y1 = model.addVar(lb=0, ub=project2_limit, name="x_project2_y1")
    x_project3_y2 = model.addVar(lb=0, ub=project3_limit, name="x_project3_y2")
    x_project4_y3 = model.addVar(lb=0, ub=project4_limit, name="x_project4_y3")

    cash_after_y1 = model.addVar(lb=0, name="cash_after_y1")
    cash_after_y2 = model.addVar(lb=0, name="cash_after_y2")
    cash_after_y3 = model.addVar(lb=0, name="cash_after_y3")

    final_amount = model.addVar(lb=0, name="final_amount")

    model.setObjective(final_amount, sense=GRB.MAXIMIZE)

    # Constraints
    # cash_after_y1 balance: cash after year 1 investments
    model.addConstr(cash_after_y1 == initial_fund - x_annual_y1 - x_project2_y1, name="cash_after_y1_balance")

    # Year 2 availability: can invest in year 2 from available cash
    available_y2 = cash_after_y1 + annual_return * x_annual_y1
    model.addConstr(x_annual_y2 + x_project3_y2 <= available_y2, name="invest_y2_cap")

    # cash after year 2
    model.addConstr(cash_after_y2 == available_y2 - x_annual_y2 - x_project3_y2, name="cash_after_y2_balance")

    # Year 3 availability
    available_y3 = cash_after_y2 + annual_return * x_annual_y2 + project2_return * x_project2_y1 + project3_return * x_project3_y2
    model.addConstr(x_annual_y3 + x_project4_y3 <= available_y3, name="invest_y3_cap")

    # cash after year 3
    model.addConstr(cash_after_y3 == available_y3 - x_annual_y3 - x_project4_y3, name="cash_after_y3_balance")

    # Final amount at end of year 3
    model.addConstr(final_amount == cash_after_y3 + annual_return * x_annual_y3 + project4_return * x_project4_y3, name="final_amount_calc")

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

    # Status string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    solution = {}
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
        solution[key] = float(variables[key].X)

    objective = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }