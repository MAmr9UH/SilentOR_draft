import math
from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    # Prepare data
    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]
    oils = veg_oils + nonveg_oils
    months = data["months"]

    model = Model()

    # Decision variables containers
    buy = {}
    use = {}
    store = {}
    y = {}

    variables_keys = {}

    # Create variables
    for oil in oils:
        for m in months:
            buy_name = f"buy_{oil}_{m}"
            use_name = f"use_{oil}_{m}"
            store_name = f"store_{oil}_{m}"
            y_name = f"y_{oil}_{m}"

            buy[(oil, m)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=buy_name)
            use[(oil, m)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=use_name)
            store[(oil, m)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=store_name)
            y[(oil, m)] = model.addVar(vtype=GRB.BINARY, name=y_name)

            variables_keys[buy_name] = buy[(oil, m)]
            variables_keys[use_name] = use[(oil, m)]
            variables_keys[store_name] = store[(oil, m)]
            variables_keys[y_name] = y[(oil, m)]

    # Objective: maximize revenue from production minus purchase costs minus storage costs
    sell_price = data["sell_price"]
    storage_cost = data["storage_cost_per_ton_month"]

    revenue = quicksum(sell_price * use[(oil, m)] for oil in oils for m in months)
    cost_purchase = quicksum(data["purchase_price"][m][oil] * buy[(oil, m)] for oil in oils for m in months)
    cost_storage = quicksum(storage_cost * store[(oil, m)] for oil in oils for m in months)

    model.setObjective(revenue - cost_purchase - cost_storage, GRB.MAXIMIZE)

    # Parameters
    initial_storage = data["initial_storage_per_oil"]
    final_storage = data["required_final_storage_per_oil"]
    storage_cap = data["storage_cap_per_oil"]
    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]

    # Constraints

    # 1) Refining capacity per month
    for m in months:
        veg_use_sum = quicksum(use[(oil, m)] for oil in veg_oils)
        nonveg_use_sum = quicksum(use[(oil, m)] for oil in nonveg_oils)

        model.addConstr(veg_use_sum <= veg_cap, name=f"veg_cap_{m}")
        model.addConstr(nonveg_use_sum <= nonveg_cap, name=f"nonveg_cap_{m}")

        # At most three oils used per month
        total_used_oils = quicksum(y[(oil, m)] for oil in oils)
        model.addConstr(total_used_oils <= 3, name=f"three_oils_{m}")

        # If an oil is used, at least 20 tons must be used
        for oil in oils:
            model.addConstr(use[(oil, m)] >= 20 * y[(oil, m)], name=f"use_min_{oil}_{m}")

        # If VEG1 or VEG2 used, then OIL3 must be used
        for veg in veg_oils:
            model.addConstr(y[(veg, m)] <= y[("OIL3", m)], name=f"veg_requires_oil3_{veg}_{m}")

    # 2) Flow balance and storage
    for oil in oils:
        for idx, m in enumerate(months):
            buy_om = buy[(oil, m)]
            use_om = use[(oil, m)]
            store_om = store[(oil, m)]

            if m == months[0]:  # January
                model.addConstr(store_om == initial_storage + buy_om - use_om, name=f"flow_{oil}_{m}")
            else:
                prev_m = months[idx - 1]
                store_prev = store[(oil, prev_m)]
                model.addConstr(store_om == store_prev + buy_om - use_om, name=f"flow_{oil}_{m}")

            # Storage cap per month per oil
            model.addConstr(store_om <= storage_cap, name=f"stor_cap_{oil}_{m}")

        # End constraint: final storage must be final_storage for each oil
        model.addConstr(store[(oil, months[-1])] == final_storage, name=f"final_store_{oil}")

    # 3) All storage non-negativity already via lb=0

    # 4) Note: Variables and model are built; return
    variables = {
        "variables_keys": variables_keys,
        "note": "Keys buy_<OIL>_<MONTH>, use_<OIL>_<MONTH>, store_<OIL>_<MONTH>, y_<OIL>_<MONTH>."
    }

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_value = model.ObjVal

    # Extract solution values
    solution = {}
    for key, var in variables["variables_keys"].items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(objective_value) if objective_value is not None else None,
        "solution": solution
    }