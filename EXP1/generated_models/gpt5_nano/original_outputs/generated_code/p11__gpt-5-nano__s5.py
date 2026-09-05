import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    months = list(data['months'])
    veg_oils = list(data['vegetable_oils'])
    nonveg_oils = list(data['non_vegetable_oils'])
    oils = veg_oils + nonveg_oils

    storage_cap = data['storage_cap_per_oil']
    initial_stock = data['initial_storage_per_oil']
    final_stock = data['required_final_storage_per_oil']
    sell_price = data['sell_price']
    storage_cost = data['storage_cost_per_ton_month']

    veg_cap = data['veg_refine_cap']
    nonveg_cap = data['nonveg_refine_cap']

    min_h = data['min_hardness']
    max_h = data['max_hardness']
    hardness = data['hardness']

    M = 100000.0  # big-M for linking y and use

    # Decision variables
    buy = {}
    use = {}
    store = {}
    y = {}

    variables = {}

    for oil in oils:
        for month in months:
            key_buy = f"buy_{oil}_{month}"
            v_buy = model.addVar(lb=0.0, name=key_buy)
            buy[(oil, month)] = v_buy
            variables[key_buy] = v_buy

            key_use = f"use_{oil}_{month}"
            v_use = model.addVar(lb=0.0, name=key_use)
            use[(oil, month)] = v_use
            variables[key_use] = v_use

            key_store = f"store_{oil}_{month}"
            v_store = model.addVar(lb=0.0, ub=storage_cap, name=key_store)
            store[(oil, month)] = v_store
            variables[key_store] = v_store

            key_y = f"y_{oil}_{month}"
            v_y = model.addVar(vtype=GRB.BINARY, name=key_y)
            y[(oil, month)] = v_y
            variables[key_y] = v_y

    # Objective components
    # Total revenue
    revenue = gp.quicksum(use[(oil, month)] for oil in oils for month in months)
    revenue = revenue * sell_price  # 150 * total monthly usage

    # Total purchase cost
    purchase_cost = gp.quicksum(use[(o, m)] * 0 for o in oils for m in months)  # placeholder to keep syntax
    purchase_cost = gp.quicksum(buy[(oil, month)] * data['purchase_price'][month][oil]
                              for oil in oils for month in months)

    # Storage cost
    storage_cost_total = gp.quicksum(store[(oil, month)] * storage_cost
                                     for oil in oils for month in months)

    obj = revenue - purchase_cost - storage_cost_total
    model.setObjective(obj, GRB.MAXIMIZE)

    # Stock balance constraints
    for oil in oils:
        prev = initial_stock
        for idx, month in enumerate(months):
            if idx == 0:
                model.addConstr(prev + buy[(oil, month)] - use[(oil, month)] == store[(oil, month)],
                                name=f"stockbal_{oil}_{month}")
            else:
                prev_store = store[(oil, months[idx - 1])]
                model.addConstr(prev_store + buy[(oil, month)] - use[(oil, month)] == store[(oil, month)],
                                name=f"stockbal_{oil}_{month}")

        # Final stock constraint: end of June must be final_stock
        model.addConstr(store[(oil, months[-1])] == final_stock, name=f"final_stock_{oil}")

    # Refining capacities
    for month in months:
        veg_total = gp.quicksum(use[(oil, month)] for oil in veg_oils)
        model.addConstr(veg_total <= veg_cap, name=f"veg_ref_cap_{month}")

        nonveg_total = gp.quicksum(use[(oil, month)] for oil in nonveg_oils)
        model.addConstr(nonveg_total <= nonveg_cap, name=f"nonveg_ref_cap_{month}")

    # Oil usage restriction: at most three oils per month
    for month in months:
        total_used_oils = gp.quicksum(y[(oil, month)] for oil in oils)
        model.addConstr(total_used_oils <= 3, name=f"oil_count_{month}")

        # If VEG1 or VEG2 used, OIL3 must be used
        model.addConstr(y[("VEG1", month)] <= y[("OIL3", month)], name=f"veg1_requires_oil3_{month}")
        model.addConstr(y[("VEG2", month)] <= y[("OIL3", month)], name=f"veg2_requires_oil3_{month}")

    # Logical constraints: if an oil is used, at least 20 tons must be used
    for oil in oils:
        for month in months:
            model.addConstr(use[(oil, month)] <= M * y[(oil, month)], name=f"use_if_y_{oil}_{month}")
            model.addConstr(use[(oil, month)] >= 20.0 * y[(oil, month)], name=f"min_use_if_y_{oil}_{month}")

    # Hardness constraints (weighted average)
    for month in months:
        total_use = gp.quicksum(use[(oil, month)] for oil in oils)
        hardness_sum = gp.quicksum(hardness[oil] * use[(oil, month)] for oil in oils)
        model.addConstr(hardness_sum >= min_h * total_use, name=f"hardness_min_{month}")
        model.addConstr(hardness_sum <= max_h * total_use, name=f"hardness_max_{month}")

    # Attach and return
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(status)

    obj_val = float(model.ObjVal)

    # Prepare solution dict in required key order
    oil_order = data['vegetable_oils'] + data['non_vegetable_oils']
    month_order = list(data['months'])
    types = ["buy", "use", "store", "y"]

    solution = {}

    for oil in oil_order:
        for month in month_order:
            for t in types:
                key = f"{t}_{oil}_{month}"
                var = variables.get(key)
                solution[key] = float(var.X) if var is not None else None

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }