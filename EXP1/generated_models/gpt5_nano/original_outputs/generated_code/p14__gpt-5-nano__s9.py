from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    """
    Builds and returns a Gurobi model and a dictionary of variables.
    The function does not call optimize().
    """
    centers = data["centers"]  # e.g., ["c1","c2","c3","c4"]
    stores = data["stores"]    # e.g., ["s1","s2",...,"s8"]
    opening_cost = data["fixed_opening_cost"]  # dict: {"c1":..., ...}
    transport_cost = data["transport_cost"]      # dict: {"c1": {"s1": ..., ...}, ...}
    demand = data["demand"]                  # dict: {"s1": ..., ...}
    capacity = data["capacity"]              # dict: {"c1": ..., ...}

    model = Model()

    # Decision variables
    # y_c: binary variable indicating if center c is opened
    y_vars = {}
    for c in centers:
        y_vars[c] = model.addVar(vtype=GRB.BINARY, name=f"y_{c}", obj=0.0)

    # f_c_s: amount shipped from center c to store s
    f_vars = {}
    for c in centers:
        for idx, s in enumerate(stores, start=1):
            vname = f"f_{c}_s{idx}"
            f_vars[(c, idx)] = model.addVar(vtype=GRB.CONTINUOUS, name=vname, lb=0.0, obj=0.0)

    model.update()  # Ensure var objects are created

    # Objective: minimize opening costs + transportation costs
    open_cost_term = quicksum(opening_cost[c] * y_vars[c] for c in centers)

    transport_term = quicksum(
        transport_cost[c][stores[idx-1]] * f_vars[(c, idx)]
        for c in centers
        for idx, _ in enumerate(stores, start=1)
    )

    model.setObjective(open_cost_term + transport_term, GRB.MINIMIZE)

    # Constraints
    # 1) Demand satisfaction: sum_c f_{c,s} == demand[s] for each store s
    for idx, s in enumerate(stores, start=1):
        demand_s = demand[s]
        model.addConstr(quicksum(f_vars[(c, idx)] for c in centers) == demand_s,
                        name=f"Demand_{s}")

    # 2) Capacity constraints: sum_s f_{c,s} <= capacity[c] * y_c for each center c
    for c in centers:
        cap_c = capacity[c]
        model.addConstr(quicksum(f_vars[(c, idx)] for idx in range(1, len(stores) + 1)) <= cap_c * y_vars[c],
                        name=f"Cap_{c}")

    # Return the model and a flat dict of variables with exactly the required keys
    variables = {}

    # y variables
    for c in centers:
        key = f"y_{c}"
        variables[key] = y_vars[c]

    # f variables
    for c in centers:
        for idx, s in enumerate(stores, start=1):
            key = f"f_{c}_s{idx}"
            variables[key] = f_vars[(c, idx)]

    return model, variables


def solve(data: dict):
    """
    Builds the model, solves it, and returns the result in the exact schema required.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to a string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    # Collect solution values
    centers = data["centers"]
    stores = data["stores"]

    solution = {}

    # y variables
    for c in centers:
        key = f"y_{c}"
        solution[key] = variables[key].X

    # f variables
    for c in centers:
        for idx, s in enumerate(stores, start=1):
            key = f"f_{c}_s{idx}"
            solution[key] = variables[key].X

    result = {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result