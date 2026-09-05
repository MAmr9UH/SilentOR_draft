import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    m = gp.Model()

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]

    max_shirts = int(min(labor_avail / labor_per_unit["shirts"], cloth_avail / cloth_per_unit["shirts"]))
    max_shorts = int(min(labor_avail / labor_per_unit["shorts"], cloth_avail / cloth_per_unit["shorts"]))
    max_pants = int(min(labor_avail / labor_per_unit["pants"], cloth_avail / cloth_per_unit["pants"]))

    shirts = m.addVar(lb=0.0, ub=max_shirts, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = m.addVar(lb=0.0, ub=max_shorts, vtype=GRB.CONTINUOUS, name="shorts")
    pants = m.addVar(lb=0.0, ub=max_pants, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = m.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = m.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = m.addVar(vtype=GRB.BINARY, name="y_pants")

    m.addConstr(3 * shirts + 2 * shorts + 6 * pants <= labor_avail, name="labor")
    m.addConstr(4 * shirts + 3 * shorts + 4 * pants <= cloth_avail, name="cloth")

    m.addConstr(shirts <= max_shirts * y_shirts, name="link_shirts")
    m.addConstr(shorts <= max_shorts * y_shorts_m, name="link_shorts")
    m.addConstr(pants <= max_pants * y_pants, name="link_pants")

    unit_contrib = data["unit_contribution"]
    rental_cost = data["rental_cost"]

    obj = (unit_contrib["shirts"] * shirts +
           unit_contrib["shorts"] * shorts +
           unit_contrib["pants"] * pants -
           rental_cost["shirts"] * y_shirts -
           rental_cost["shorts"] * y_shorts_m -
           rental_cost["pants"] * y_pants)

    m.setObjective(obj, GRB.MAXIMIZE)

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

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_code, str(status_code))

    objective_value = model.ObjVal if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) else None
    if objective_value is not None:
        objective_value = float(objective_value)

    sol = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": sol
    }