import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]

    # Compute upper bounds on production to set big-M for machinery constraints
    max_shirts = min(labor_avail / labor_per_unit["shirts"], cloth_avail / cloth_per_unit["shirts"])
    max_shorts = min(labor_avail / labor_per_unit["shorts"], cloth_avail / cloth_per_unit["shorts"])
    max_pants = min(labor_avail / labor_per_unit["pants"], cloth_avail / cloth_per_unit["pants"])

    # Decision variables
    shirts = m.addVar(lb=0.0, ub=max_shirts, vtype=GRB.CONTINUOUS, name="shirts_produced")
    shorts = m.addVar(lb=0.0, ub=max_shorts, vtype=GRB.CONTINUOUS, name="shorts_produced")
    pants = m.addVar(lb=0.0, ub=max_pants, vtype=GRB.CONTINUOUS, name="pants_produced")

    y_shirts = m.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = m.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = m.addVar(vtype=GRB.BINARY, name="y_pants")

    # Constraints
    m.addConstr(labor_per_unit["shirts"] * shirts +
                labor_per_unit["shorts"] * shorts +
                labor_per_unit["pants"] * pants <= labor_avail, name="labor_limit")

    m.addConstr(cloth_per_unit["shirts"] * shirts +
                cloth_per_unit["shorts"] * shorts +
                cloth_per_unit["pants"] * pants <= cloth_avail, name="cloth_limit")

    m.addConstr(shirts <= max_shirts * y_shirts, name="mach_shirts")
    m.addConstr(shorts <= max_shorts * y_shorts_m, name="mach_shorts")
    m.addConstr(pants <= max_pants * y_pants, name="mach_pants")

    # Objective: maximize contribution minus rental costs
    unit_contrib = data["unit_contribution"]
    rental_cost = data["rental_cost"]

    objective = (unit_contrib["shirts"] * shirts +
                 unit_contrib["shorts"] * shorts +
                 unit_contrib["pants"] * pants -
                 rental_cost["shirts"] * y_shirts -
                 rental_cost["shorts"] * y_shorts_m -
                 rental_cost["pants"] * y_pants)

    m.setObjective(objective, GRB.MAXIMIZE)

    m.update()

    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))

    model.update()

    shirts_val = variables["shirts"].X
    shorts_val = variables["shorts"].X
    pants_val = variables["pants"].X
    y_shirts_val = variables["y_shirts"].X
    y_shorts_m_val = variables["y_shorts_m"].X
    y_pants_val = variables["y_pants"].X

    solution = {
        "shirts": float(shirts_val),
        "shorts": float(shorts_val),
        "pants": float(pants_val),
        "y_shirts": float(y_shirts_val),
        "y_shorts_m": float(y_shorts_m_val),
        "y_pants": float(y_pants_val)
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }