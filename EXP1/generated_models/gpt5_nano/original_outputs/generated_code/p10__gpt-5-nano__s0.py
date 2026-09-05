from gurobipy import Model, GRB

def build_model(data: dict):
    m = Model()

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]
    unit_contribution = data["unit_contribution"]
    rental_costs = data["rental_cost"]

    # Decision variables
    shirts = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shorts")
    pants = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = m.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = m.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = m.addVar(vtype=GRB.BINARY, name="y_pants")

    m.update()

    # Objective: max profit = contribution margin - rental costs
    objective = (
        unit_contribution["shirts"] * shirts +
        unit_contribution["shorts"] * shorts +
        unit_contribution["pants"] * pants -
        rental_costs["shirts"] * y_shirts -
        rental_costs["shorts"] * y_shorts_m -
        rental_costs["pants"] * y_pants
    )
    m.setObjective(objective, GRB.MAXIMIZE)

    # Constraints
    m.addConstr(
        labor_per_unit["shirts"] * shirts +
        labor_per_unit["shorts"] * shorts +
        labor_per_unit["pants"] * pants <= labor_avail,
        name="labor"
    )

    m.addConstr(
        cloth_per_unit["shirts"] * shirts +
        cloth_per_unit["shorts"] * shorts +
        cloth_per_unit["pants"] * pants <= cloth_avail,
        name="cloth"
    )

    # Big-M linking constraints: produce > 0 implies rental is made
    M_shirts = min(labor_avail / labor_per_unit["shirts"], cloth_avail / cloth_per_unit["shirts"])
    M_shorts = min(labor_avail / labor_per_unit["shorts"], cloth_avail / cloth_per_unit["shorts"])
    M_pants = min(labor_avail / labor_per_unit["pants"], cloth_avail / cloth_per_unit["pants"])

    m.addConstr(shirts <= M_shirts * y_shirts, name="link_shirts")
    m.addConstr(shorts <= M_shorts * y_shorts_m, name="link_shorts")
    m.addConstr(pants <= M_pants * y_pants, name="link_pants")

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

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result