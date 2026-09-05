import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    model = gp.Model()

    # Define oils and months
    vegetable_oils = data["vegetable_oils"]
    non_vegetable_oils = data["non_vegetable_oils"]
    oils = vegetable_oils + non_vegetable_oils
    months = data["months"]

    # Storage and refinement constraints parameters
    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]
    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    initial_storage = data["initial_storage_per_oil"]
    final_storage = data["required_final_storage_per_oil"]

    hardness = data["hardness"]
    sell_price = data["sell_price"]

    # Containers for variables
    vars_by_key = {}

    # Helper to create continuous/binary vars and register them
    def add_var(vtype, key, **kwargs):
        var = model.addVar(vtype=vtype, name=key, **kwargs)
        vars_by_key[key] = var
        return var

    # Create decision variables
    buy = {o: {} for o in oils}
    use = {o: {} for o in oils}
    store = {o: {} for o in oils}
    y = {o: {} for o in oils}

    for o in oils:
        for m in months:
            key_buy = f"buy_{o}_{m}"
            key_use = f"use_{o}_{m}"
            key_store = f"store_{o}_{m}"
            key_y = f"y_{o}_{m}"

            buy[o][m] = add_var(GRB.CONTINUOUS, key_buy, lb=0.0)
            use[o][m] = add_var(GRB.CONTINUOUS, key_use, lb=0.0)
            store[o][m] = add_var(GRB.CONTINUOUS, key_store, lb=0.0, ub=storage_cap)
            y[o][m] = add_var(GRB.BINARY, key_y)

            # Linking use with y: if used, at least 20 tons; if not used, 0
            M = 10000.0
            model.addConstr(use[o][m] <= M * y[o][m])
            model.addConstr(use[o][m] >= 20.0 * y[o][m])

    # 1) Refining capacity per month
    for m in months:
        # Vegetable oils refined per month
        model.addConstr(quicksum(use[o][m] for o in vegetable_oils) <= veg_cap)
        # Non-vegetable oils refined per month
        model.addConstr(quicksum(use[o][m] for o in non_vegetable_oils) <= nonveg_cap)

    # 2) At most three oils used in any month
    for m in months:
        model.addConstr(quicksum(y[o][m] for o in oils) <= 3)

    # 3) If VEG1 or VEG2 is used, OIL3 must be used that month
    for m in months:
        if "VEG1" in oils:
            pass
        # Enforce specifically for VEG1 and VEG2
        if "VEG1" in oils:
            model.addConstr(y["VEG1"][m] <= y["OIL3"][m])
        if "VEG2" in oils:
            model.addConstr(y["VEG2"][m] <= y["OIL3"][m])

    # 4) Storage balance equations
    # January initial storage
    for o in oils:
        model.addConstr(store[o]["Jan"] == initial_storage * 1.0 + buy[o]["Jan"] - use[o]["Jan"])
        # February to June
        for idx in range(1, len(months)):
            m_prev = months[idx - 1]
            m_cur = months[idx]
            model.addConstr(store[o][m_cur] == store[o][m_prev] + buy[o][m_cur] - use[o][m_cur])

    # 5) Final storage must be final_storage
    for o in oils:
        model.addConstr(store[o]["Jun"] == final_storage * 1.0)

    # 6) Objective: Maximize revenue from sale minus purchase costs minus storage costs
    revenue = quicksum(sell_price * use[o][m] for o in oils for m in months)
    purchase_cost = quicksum(
        data["purchase_price"][m][o] * buy[o][m] for o in oils for m in months
    )
    storage_costs = quicksum(storage_cost * store[o][m] for o in oils for m in months)

    model.setObjective(revenue - purchase_cost - storage_costs, GRB.MAXIMIZE)

    # 7) Hardness constraints per month: 3 <= weighted hardness <= 6
    for m in months:
        total_use_m = quicksum(use[o][m] for o in oils)
        hardness_sum = quicksum(use[o][m] * hardness[o] for o in oils)
        model.addConstr(hardness_sum >= 3.0 * total_use_m)
        model.addConstr(hardness_sum <= 6.0 * total_use_m)

    model.update()
    return model, {"variables_keys": vars_by_key, "note": "Keys buy_<OIL>_<MONTH>, use_<OIL>_<MONTH>, store_<OIL>_<MONTH>, y_<OIL>_<MONTH>."}

def solve(data: dict) -> dict:
    model, variables_container = build_model(data)
    model.optimize()

    # Prepare solution output
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

    # Objective value
    obj_val = float(model.ObjVal) if model.ObjVal is not None else 0.0

    # Extract values for all variables
    vars_by_key = None
    if isinstance(variables_container, dict) and "variables_keys" in variables_container:
        vars_by_key = variables_container["variables_keys"]
    else:
        vars_by_key = {}

    solution = {}
    oils = data["vegetable_oils"] + data["non_vegetable_oils"]
    months = data["months"]

    for o in oils:
        for m in months:
            for typ in ["buy", "use", "store", "y"]:
                key = f"{typ}_{o}_{m}"
                if key in vars_by_key:
                    val = float(vars_by_key[key].X) if vars_by_key[key].X is not None else 0.0
                    solution[key] = val
                else:
                    solution[key] = 0.0

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }