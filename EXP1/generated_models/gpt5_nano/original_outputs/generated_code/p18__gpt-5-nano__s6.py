import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build and return the Gurobi model and a dictionary of decision variables.
    The function does not call optimize().
    """
    centers = data["centers"]
    stores = data["stores"]

    m = gp.Model()

    # Decision variables
    y = {}
    for c in centers:
        y[c] = m.addVar(vtype=gp.GRB.BINARY, name=f"y_{c}")

    f = {}
    for c in centers:
        for s in stores:
            f[(c, s)] = m.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{c}_{s}")

    m.update()

    # Demand constraints: sum_i f_{i,s} >= demand_s
    for s in stores:
        m.addConstr(gp.quicksum(f[(c, s)] for c in centers) >= data["demand"][s], name=f"demand_{s}")

    # Capacity constraints: sum_s f_{c,s} <= capacity_c * y_c
    for c in centers:
        m.addConstr(gp.quicksum(f[(c, s)] for s in stores) <= data["capacity"][c] * y[c], name=f"capacity_{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost = gp.quicksum(data["fixed_opening_cost"][c] * y[c] for c in centers)
    transport_cost = gp.quicksum(
        data["transport_cost"][c][s] * f[(c, s)] for c in centers for s in stores
    )
    m.setObjective(opening_cost + transport_cost, gp.GRB.MINIMIZE)

    # Build the output variable dictionary with exact keys
    variables = {}
    for c in centers:
        variables[f"y_{c}"] = y[c]
    for c in centers:
        for s in stores:
            variables[f"f_{c}_{s}"] = f[(c, s)]

    return m, variables

def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return a solution dictionary with:
    - status: string representation of the solver status
    - objective: minimum total cost
    - solution: values of all decision variables with exact keys
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    st = model.Status
    if st == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    obj = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": obj,
        "solution": solution
    }