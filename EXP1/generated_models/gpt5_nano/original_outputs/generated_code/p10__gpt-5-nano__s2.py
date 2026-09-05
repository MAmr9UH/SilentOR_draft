import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    labor_avail = data["labor_available"]
    cloth_avail = data["cloth_available"]

    labor_per_unit = data["labor_per_unit"]
    cloth_per_unit = data["cloth_per_unit"]
    unit_contribution = data["unit_contribution"]
    rental_cost = data["rental_cost"]

    # Compute upper bounds for production based on resource limits
    ub = {}
    ub["shirts"] = int(min(labor_avail // labor_per_unit["shirts"],
                         cloth_avail // cloth_per_unit["shirts"]))
    ub["shorts"] = int(min(labor_avail // labor_per_unit["shorts"],
                          cloth_avail // cloth_per_unit["shorts"]))
    ub["pants"] = int(min(labor_avail // labor_per_unit["pants"],
                         cloth_avail // cloth_per_unit["pants"]))

    # Decision variables
    shirts = model.addVar(lb=0.0, ub=ub["shirts"], vtype=gp.GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(lb=0.0, ub=ub["shorts"], vtype=gp.GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(lb=0.0, ub=ub["pants"], vtype=gp.GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=gp.GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=gp.GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=gp.GRB.BINARY, name="y_pants")

    model.update()

    # Constraints
    model.addConstr(3 * shirts + 2 * shorts + 6 * pants <= labor_avail, name="labor")
    model.addConstr(4 * shirts + 3 * shorts + 4 * pants <= cloth_avail, name="cloth")

    # Machinery rental linkage: production can occur only if machinery is rented
    model.addConstr(shirts <= ub["shirts"] * y_shirts, name="link_shirts")
    model.addConstr(shorts <= ub["shorts"] * y_shorts_m, name="link_shorts")
    model.addConstr(pants <= ub["pants"] * y_pants, name="link_pants")

    # Objective: maximize contribution minus rental costs
    objective = (
        unit_contribution["shirts"] * shirts +
        unit_contribution["shorts"] * shorts +
        unit_contribution["pants"] * pants -
        rental_cost["shirts"] * y_shirts -
        rental_cost["shorts"] * y_shorts_m -
        rental_cost["pants"] * y_pants
    )
    model.setObjective(objective, sense=gp.GRB.MAXIMIZE)

    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return model, variables

def _status_to_string(status: int) -> str:
    if status == gp.GRB.OPTIMAL:
        return "OPTIMAL"
    if status == gp.GRB.INFEASIBLE:
        return "INFEASIBLE"
    if status == gp.GRB.UNBOUNDED:
        return "UNBOUNDED"
    if status == gp.GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if status == gp.GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    return str(status)

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_str = _status_to_string(model.Status)
    obj_val = float(model.ObjVal) if model.Status == gp.GRB.OPTIMAL else float("nan")

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }