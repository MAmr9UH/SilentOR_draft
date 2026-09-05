import gurobipy as gp

def build_model(data: dict) -> tuple:
    centers = data["centers"]
    stores = data["stores"]

    model = gp.Model()
    model.Params.LogToConsole = 0  # keep quiet
    variables = {}

    # Decision variables: opening decisions
    for c in centers:
        vars_name = f"y_{c}"
        yv = model.addVar(vtype=gp.GRB.BINARY, name=vars_name)
        variables[vars_name] = yv

    # Decision variables: shipments from center to store
    for c in centers:
        for s in stores:
            var_name = f"f_{c}_{s}"
            fv = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=var_name)
            variables[var_name] = fv

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.quicksum(opening_costs[c] * variables[f"y_{c}"] for c in centers)
    for c in centers:
        for s in stores:
            obj += transport_cost[c][s] * variables[f"f_{c}_{s}"]
    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Constraints

    # 1) Demand satisfaction at each store
    for s in stores:
        model.addConstr(gp.quicksum(variables[f"f_{c}_{s}"] for c in centers) >= data["demand"][s],
                        name=f"dem_{s}")

    # 2) Capacity constraints for each center (only if opened)
    for c in centers:
        model.addConstr(gp.quicksum(variables[f"{c}_{s}"] for s in stores) <= data["capacity"][c] * variables[f"y_{c}"],
                        name=f"cap_{c}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    centers = data["centers"]
    stores = data["stores"]

    # Status as string
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(int(model.Status), str(model.Status))

    # Objective value
    objective_value = float(model.ObjVal)

    # Build solution dict with all required keys
    solution = {}
    for c in centers:
        key = f"y_{c}"
        solution[key] = float(variables[key].X)
    for c in centers:
        for s in stores:
            key = f"f_{c}_{s}"
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }