import gurobipy as gp

def build_model(data: dict):
    """
    Build the Gurobi model for the distribution center location and transportation problem.
    Returns the model and a flat dictionary of all decision variables with exact keys as required.
    """
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # y_c: 1 if center c is opened
    for c in centers:
        key = f"y_{c}"
        variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    # f_c_s: units shipped from center c to store s
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            variables[key] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=key)

    model.update()

    # Objective: minimize opening costs + transportation costs
    obj = gp.quicksum(data["fixed_opening_cost"][c] * variables[f"y_{c}"] for c in centers)
    for c in centers:
        for s in stores:
            obj += data["transport_cost"][c][s] * variables[f"f_{c}_{s}"]
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraints

    # Demands: sum_c f_{c_s} == demand_s for each store s
    for s in stores:
        model.addConstr(
            gp.quicksum(variables[f"f_{c}_{s}"] for c in centers) == data["demand"][s],
            name=f"Dem_{s}"
        )

    # Capacities: sum_s f_{c_s} <= capacity_c * y_c for each center c
    for c in centers:
        model.addConstr(
            gp.quicksum(variables[f"f_{c}_{s}"] for s in stores) <= data["capacity"][c] * variables[f"y_{c}"],
            name=f"Cap_{c}"
        )

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status interpretation
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    # Objective value
    objective_value = float(model.ObjVal)

    # Solution dictionary with exact keys
    solution = {}

    # y variables
    for c in data["centers"]:
        solution[f"y_{c}"] = float(variables[f"y_{c}"].X)

    # f variables
    for c in data["centers"]:
        for s in data["stores"]:
            solution[f"f_{c}_{s}"] = float(variables[f"f_{c}_{s}"].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }