import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()

    months = data["months"]
    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]
    oils = veg_oils + nonveg_oils

    # Parameters
    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]
    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    initial_store = data.get("initial_storage_per_oil", 0)  # assumed same for all oils if scalar
    final_store_req = data.get("required_final_storage_per_oil", 0)
    min_hard = data.get("min_hardness", 0)
    max_hard = data.get("max_hardness", 0)
    sell_price = data["sell_price"]

    # hardness per oil
    hardness = data["hardness"]

    # price per month per oil
    purchase_price = data["purchase_price"]

    M = 1e6  # big-M

    # Decision variables
    buy = {}
    use = {}
    store = {}
    y = {}

    for oil in oils:
        for m in months:
            buy[oil, m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"buy_{oil}_{m}")
            use[oil, m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"use_{oil}_{m}")
            store[oil, m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"store_{oil}_{m}")
            y[oil, m] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{oil}_{m}")

    model.update()

    # Linking use with y
    for oil in oils:
        for m in months:
            model.addConstr(use[oil, m] <= M * y[oil, m])
            model.addConstr(use[oil, m] >= 20 * y[oil, m])

    # At most three oils used per month
    for m in months:
        model.addConstr(gp.quicksum(y[o, m] for o in oils) <= 3)

    # If VEG1 or VEG2 used, OIL3 must be used
    if "VEG1" in oils:
        for m in months:
            model.addConstr(y["VEG1", m] <= y["OIL3", m])
    if "VEG2" in oils:
        for m in months:
            model.addConstr(y["VEG2", m] <= y["OIL3", m])

    # Refining capacity per month
    for m in months:
        veg_sum = gp.quicksum(use[o, m] for o in veg_oils)
        nonveg_sum = gp.quicksum(use[o, m] for o in nonveg_oils)
        model.addConstr(veg_sum <= veg_cap)
        model.addConstr(nonveg_sum <= nonveg_cap)

    # Hardness constraints: final product hardness between 3 and 6
    for m in months:
        sum_h = gp.quicksum(hardness[o] * use[o, m] for o in oils)
        sum_u = gp.quicksum(use[o, m] for o in oils)
        model.addConstr(sum_h >= min_hard * sum_u)
        model.addConstr(sum_h <= max_hard * sum_u)

    # Storage balance
    # January balances with initial storage
    for oil in oils:
        model.addConstr(store[oil, "Jan"] == initial_store + buy[oil, "Jan"] - use[oil, "Jan"])

    # Balance February to June
    for i in range(1, len(months)):
        m = months[i]
        pm = months[i - 1]
        for oil in oils:
            model.addConstr(store[oil, m] == store[oil, pm] + buy[oil, m] - use[oil, m])

    # End of June final storage equals required final storage per oil
    for oil in oils:
        model.addConstr(store[oil, months[-1]] == final_store_req)

    # Storage capacity per oil
    for oil in oils:
        for m in months:
            model.addConstr(store[oil, m] <= storage_cap)

            # Non-negativity is already ensured by variable bounds

    model.update()

    # Objective: maximize profit
    # Revenue from final product: sell_price * total used in each month
    revenue = gp.quicksum(sell_price * gp.quicksum(use[o, m] for o in oils) for m in months)

    # Cost of purchases
    cost = gp.quicksum(buy[o, m] * purchase_price[m][o] for o in oils for m in months)

    # Storage costs
    storage_cost_expr = storage_cost * gp.quicksum(store[o, m] for o in oils for m in months)

    model.setObjective(revenue - cost - storage_cost_expr, sense=gp.GRB.MAXIMIZE)

    # Collect all variables into a single dict with exact keys
    variables = {}
    for oil in oils:
        for m in months:
            variables[f"buy_{oil}_{m}"] = buy[oil, m]
            variables[f"use_{oil}_{m}"] = use[oil, m]
            variables[f"store_{oil}_{m}"] = store[oil, m]
            variables[f"y_{oil}_{m}"] = y[oil, m]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(status)

    obj_val = model.ObjVal if model.NumObj > -1 else None

    # Build solution dict in exact order expected
    oils_order = data["vegetable_oils"] + data["non_vegetable_oils"]
    months_order = data["months"]

    solution = {}

    # Buy variables
    for oil in oils_order:
        for m in months_order:
            key = f"buy_{oil}_{m}"
            solution[key] = float(variables[key].X)

    # Use variables
    for oil in oils_order:
        for m in months_order:
            key = f"use_{oil}_{m}"
            solution[key] = float(variables[key].X)

    # Store variables
    for oil in oils_order:
        for m in months_order:
            key = f"store_{oil}_{m}"
            solution[key] = float(variables[key].X)

    # Binary usage indicators
    for oil in oils_order:
        for m in months_order:
            key = f"y_{oil}_{m}"
            solution[key] = float(variables[key].X)

    result = {
        "status": status_str,
        "objective": float(obj_val) if obj_val is not None else None,
        "solution": solution
    }

    return result