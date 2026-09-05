def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    model = gp.Model("garment_profit")

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    unit_contrib = data["unit_contribution"]
    rental_cost = data["rental_cost"]
    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]

    # Decision variables
    shirts = model.addVar(vtype=GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(vtype=GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=GRB.BINARY, name="y_pants")

    # Resource constraints
    model.addConstr(3 * shirts + 2 * shorts + 6 * pants <= labor_avail, name="labor")
    model.addConstr(4 * shirts + 3 * shorts + 4 * pants <= cloth_avail, name="cloth")

    # Upper bounds for linking constraints (Big-M)
    M_shirts = min(labor_avail / labor_per_unit["shirts"], cloth_avail / cloth_per_unit["shirts"])
    M_shorts = min(labor_avail / labor_per_unit["shorts"], cloth_avail / cloth_per_unit["shorts"])
    M_pants = min(labor_avail / labor_per_unit["pants"], cloth_avail / cloth_per_unit["pants"])

    model.addConstr(shirts <= M_shirts * y_shirts, name="link_shirts")
    model.addConstr(shorts <= M_shorts * y_shorts_m, name="link_shorts")
    model.addConstr(pants <= M_pants * y_pants, name="link_pants")

    # Objective: maximize profit (unit contribution minus rental costs)
    objective = (
        unit_contrib["shirts"] * shirts +
        unit_contrib["shorts"] * shorts +
        unit_contrib["pants"] * pants
        - rental_cost["shirts"] * y_shirts
        - rental_cost["shorts"] * y_shorts_m
        - rental_cost["pants"] * y_pants
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    model.update()

    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return model, variables


def solve(data: dict) -> dict:
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_str = str(status_int)
    # Map common statuses to strings for readability
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.CUTOFF: "CUTOFF",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.INTERRUPTED: "INTERRUPTED",
    }
    status_str = status_map.get(status_int, status_str)

    objective = float(model.ObjVal)

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }