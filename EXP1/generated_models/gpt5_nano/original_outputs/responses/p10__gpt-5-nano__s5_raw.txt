import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    contributions = data["unit_contribution"]
    rental = data["rental_cost"]

    labor_total = data["labor_available"]
    cloth_total = data["cloth_available"]

    # Decision variables
    shirts = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=gp.GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=gp.GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=gp.GRB.BINARY, name="y_pants")

    # Big-M
    M = 1000.0

    # Constraints
    model.addConstr(3 * shirts + 2 * shorts + 6 * pants <= labor_total, name="labor")
    model.addConstr(4 * shirts + 3 * shorts + 4 * pants <= cloth_total, name="cloth")

    model.addConstr(shirts <= M * y_shirts, name="activate_shirts")
    model.addConstr(shorts <= M * y_shorts_m, name="activate_shorts")
    model.addConstr(pants <= M * y_pants, name="activate_pants")

    # Objective: maximize profit = contribution - rental
    obj = (contributions["shirts"] * shirts +
           contributions["shorts"] * shorts +
           contributions["pants"] * pants -
           rental["shirts"] * y_shirts -
           rental["shorts"] * y_shorts_m -
           rental["pants"] * y_pants)

    model.setObjective(obj, gp.GRB.MAXIMIZE)

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
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_int, str(status_int))

    obj_val = model.ObjVal

    solution_values = {
        "shirts": variables["shirts"].X,
        "shorts": variables["shorts"].X,
        "pants": variables["pants"].X,
        "y_shirts": variables["y_shirts"].X,
        "y_shorts_m": variables["y_shorts_m"].X,
        "y_pants": variables["y_pants"].X
    }

    # Cast to floats to ensure JSON-serializable numbers
    solution = {k: float(v) for k, v in solution_values.items()}

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }