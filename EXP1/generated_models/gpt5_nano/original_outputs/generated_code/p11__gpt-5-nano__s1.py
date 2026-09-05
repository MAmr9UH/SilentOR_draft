import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model("OilBlending")

    oils = data["vegetable_oils"] + data["non_vegetable_oils"]
    months = data["months"]

    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]

    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]

    veg_refine_cap = data["veg_refine_cap"]
    nonveg_refine_cap = data["nonveg_refine_cap"]

    min_hard = data["min_hardness"]
    max_hard = data["max_hardness"]
    hardness = data["hardness"]

    initial_store = data["initial_storage_per_oil"]
    final_store_req = data["required_final_storage_per_oil"]

    sell_price = data["sell_price"]

    # Price data by (oil, month)
    price = {}
    for month in months:
        price[month] = data["purchase_price"][month]

    # Decision variables
    buy = {}
    use = {}
    store = {}
    y = {}

    # Flattened variable map for output
    variables = {}

    for oil in oils:
        for month in months:
            b = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name=f"buy_{oil}_{month}")
            u = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name=f"use_{oil}_{month}")
            s = model.addVar(lb=0.0, ub=storage_cap, vtype=gp.GRB.CONTINUOUS, name=f"store_{oil}_{month}")
            yy = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{oil}_{month}")

            buy[(oil, month)] = b
            use[(oil, month)] = u
            store[(oil, month)] = s
            y[(oil, month)] = yy

            key_base = f"{'buy' if True else 'x'}_{oil}_{month}"
            variables[f"buy_{oil}_{month}"] = b
            variables[f"use_{oil}_{month}"] = u
            variables[f"store_{oil}_{month}"] = s
            variables[f"y_{oil}_{month}"] = yy

    # Objective components
    # Revenue = sell_price * total used (sum of all use variables)
    total_use = gp.quicksum(use[(oil, month)] for oil in oils for month in months)
    revenue = sell_price * total_use

    # Purchase cost
    purchase_cost = gp.quicksum(price[month][oil] * buy[(oil, month)]
                                for oil in oils for month in months)

    # Storage cost
    total_store = gp.quicksum(store[(oil, month)] for oil in oils for month in months)
    storage_cost_term = storage_cost * total_store

    model.setObjective(revenue - purchase_cost - storage_cost_term, gp.GRB.MAXIMIZE)

    # Constraints

    # Refining capacity per month
    for month in months:
        veg_use = gp.quicksum(use[(oil, month)] for oil in veg_oils)
        nonveg_use = gp.quicksum(use[(oil, month)] for oil in nonveg_oils)
        model.addConstr(veg_use <= veg_refine_cap, name=f"veg_cap_{month}")
        model.addConstr(nonveg_use <= nonveg_refine_cap, name=f"nonveg_cap_{month}")

        # At most three oils used per month
        total_oils_used = gp.quicksum(y[(oil, month)] for oil in oils)
        model.addConstr(total_oils_used <= 3, name=f"oil_count_{month}")

        # If VEG1 or VEG2 used, OIL3 must be used that month
        model.addConstr(y[("VEG1", month)] + y[("VEG2", month)] <= 2 * y[("OIL3", month)], name=f"veg_to_oil3_{month}")

        # Hardness constraints: H_m >= min_h * U_m and H_m <= max_h * U_m
        H_m = gp.quicksum(hardness[oil] * use[(oil, month)] for oil in oils)
        U_m = gp.quicksum(use[(oil, month)] for oil in oils)
        model.addConstr(H_m >= min_h * U_m, name=f"min_hard_{month}")
        model.addConstr(H_m <= max_h * U_m, name=f"max_hard_{month}")

        # Use nonzero only if binary is 1
        M = 1000
        for oil in oils:
            model.addConstr(use[(oil, month)] <= M * y[(oil, month)], name=f"use_if_{oil}_{month}")
            model.addConstr(use[(oil, month)] >= 20 * y[(oil, month)], name=f"min_use_if_{oil}_{month}")

    # Inventory balance and storage constraints
    for oil in oils:
        # Jan balance
        model.addConstr(store[(oil, "Jan")] == initial_store + buy[(oil, "Jan")] - use[(oil, "Jan")],
                        name=f"bal_Jan_{oil}")

        # Balance for subsequent months
        for idx in range(1, len(months)):
            month = months[idx]
            prev_month = months[idx - 1]
            model.addConstr(store[(oil, month)] == store[(oil, prev_month)] + buy[(oil, month)] - use[(oil, month)],
                            name=f"bal_{oil}_{month}")

        # End of June storage fixed to required final storage
        model.addConstr(store[(oil, "Jun")] == final_store_req, name=f"end_store_{oil}")

        # Non-negativity and storage cap enforced by variable bounds
        # Additionally, ensure storage does not exceed cap for all months
        for month in months:
            model.addConstr(store[(oil, month)] <= storage_cap, name=f"store_cap_{oil}_{month}")
            model.addConstr(store[(oil, month)] >= 0, name=f"store_nonneg_{oil}_{month}")

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Prepare status string
    from gurobipy import GRB
    if model.Status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif model.Status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif model.Status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif model.Status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(model.Status)

    # Collect solution values
    model.update()
    solution = {}
    for key, var in variables.items():
        try:
            solution[key] = var.X
        except:
            solution[key] = None

    return {
        "status": status_str,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution
    }