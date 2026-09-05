import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    # Initialize model
    m = gp.Model()

    # Data extraction
    months = data["months"]
    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]
    all_oils = veg_oils + nonveg_oils

    sell_price = data["sell_price"]

    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    initial_storage = data["initial_storage_per_oil"]

    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]

    hardness = data["hardness"]
    min_hard = data["min_hardness"]
    max_hard = data["max_hardness"]

    # Helper constants
    M_big = 1000  # big-M for linking y and use

    # Prepare hardness map for all oils
    h = {**hardness}

    # Variables dictionary
    variables = {}

    # Create variables for each oil and month
    for oil in all_oils:
        for m in months:
            buy_var = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"buy_{oil}_{m}")
            use_var = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"use_{oil}_{m}")
            store_var = m.addVar(lb=0.0, ub=float(storage_cap), vtype=GRB.CONTINUOUS, name=f"store_{oil}_{m}")
            y_var = m.addVar(vtype=GRB.BINARY, name=f"y_{oil}_{m}")
            variables[f"buy_{oil}_{m}"] = buy_var
            variables[f"use_{oil}_{m}"] = use_var
            variables[f"store_{oil}_{m}"] = store_var
            variables[f"y_{oil}_{m}"] = y_var

    m.update()

    # Objective: maximize revenue from product minus purchase costs minus storage costs
    obj = gp.LinExpr()

    # Revenue from final product
    for oil in all_oils:
        for m in months:
            obj += sell_price * variables[f"use_{oil}_{m}"]

    # Purchase costs
    for oil in all_oils:
        for m in months:
            price = data["purchase_price"][m][oil]
            obj -= price * variables[f"buy_{oil}_{m}"]

    # Storage costs
    for oil in all_oils:
        for m in months:
            obj -= storage_cost * variables[f"store_{oil}_{m}"]

    m.setObjective(obj, GRB.MAXIMIZE)

    # Constraints

    # 1) Flow balance: store_i_m = previous_store + buy - use
    for oil in all_oils:
        for idx, m in enumerate(months):
            store_cur = variables[f"store_{oil}_{m}"]
            buy_cur = variables[f"buy_{oil}_{m}"]
            use_cur = variables[f"use_{oil}_{m}"]
            if idx == 0:
                prev_store = initial_storage
                m.addConstr(store_cur == prev_store + buy_cur - use_cur,
                            name=f"flow_{oil}_{m}")
            else:
                prev_month = months[idx - 1]
                prev_store_var = variables[f"store_{oil}_{prev_month}"]
                m.addConstr(store_cur == prev_store_var + buy_cur - use_cur,
                            name=f"flow_{oil}_{m}")

    # Final storage must be 500 for each oil
    for oil in all_oils:
        m.addConstr(variables[f"store_{oil}_{months[-1]}"] ==  initial_storage * 1, 
                    name=f"final_storage_{oil}")

    # Storage capacity per oil
    for oil in all_oils:
        for m in months:
            m.addConstr(variables[f"store_{oil}_{m}"] <= float(storage_cap),
                        name=f"storage_cap_{oil}_{m}")

    # 2) Refining (usage) caps per month
    for m in months:
        veg_use = variables[f"use_{veg_oils[0]}_{m}"]  # VEG1
        veg_use2 = variables[f"use_{veg_oils[1]}_{m}"]  # VEG2
        nonveg_sum = sum(variables[f"use_{oil}_{m}"] for oil in nonveg_oils)
        m.addConstr(veg_use + veg_use2 <= float(veg_cap), name=f"veg_cap_{m}")
        m.addConstr(nonveg_sum <= float(nonveg_cap), name=f"nonveg_cap_{m}")

    # 3) If oil used, at least 20 tons; and at most 3 oils used per month
    for oil in all_oils:
        for m in months:
            use_var = variables[f"use_{oil}_{m}"]
            y_var = variables[f"y_{oil}_{m}"]
            m.addConstr(use_var <= M_big * y_var, name=f"use_when_dummy_{oil}_{m}")
            m.addConstr(use_var >= 20 * y_var, name=f"min_use_if_used_{oil}_{m}")

    for m in months:
        sum_y = gp.quicksum(variables[f"y_{oil}_{m}"] for oil in all_oils)
        m.addConstr(sum_y <= 3, name=f"three_oils_max_{m}")

    # 4) If VEG1 or VEG2 used, OIL3 must be used
    for m in months:
        m.addConstr(variables["y_VEG1_" + m] <= variables["y_OIL3_" + m], name=f"veg1_requires_oil3_{m}")
        m.addConstr(variables["y_VEG2_" + m] <= variables["y_OIL3_" + m], name=f"veg2_requires_oil3_{m}")

    # 5) Hardness blending constraints
    min_h = min_hard
    max_h = max_hard
    for m in months:
        sum_use = gp.quicksum(variables[f"use_{oil}_{m}"] for oil in all_oils)
        sum_h = gp.quicksum(h[oil] * variables[f"use_{oil}_{m}"] for oil in all_oils)
        m.addConstr(sum_h >= min_h * sum_use, name=f"hardness_min_{m}")
        m.addConstr(sum_h <= max_h * sum_use, name=f"hardness_max_{m}")

    m.update()
    return m, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
    }
    status_str = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal) if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT) else float('nan')

    # Build solution dictionary in required order
    solution = {}

    oils_order = data["vegetable_oils"] + data["non_vegetable_oils"]
    months = data["months"]

    # 1) Buy variables (in exact order)
    for oil in data["vegetable_oils"]:
        for m in months:
            solution[f"buy_{oil}_{m}"] = float(variables[f"buy_{oil}_{m}"].X)
    for oil in data["non_vegetable_oils"]:
        for m in months:
            solution[f"buy_{oil}_{m}"] = float(variables[f"buy_{oil}_{m}"].X)

    # 2) Use variables
    for oil in data["vegetable_oils"]:
        for m in months:
            solution[f"use_{oil}_{m}"] = float(variables[f"use_{oil}_{m}"].X)
    for oil in data["non_vegetable_oils"]:
        for m in months:
            solution[f"use_{oil}_{m}"] = float(variables[f"use_{oil}_{m}"].X)

    # 3) Store variables
    for oil in data["vegetable_oils"]:
        for m in months:
            solution[f"store_{oil}_{m}"] = float(variables[f"store_{oil}_{m}"].X)
    for oil in data["non_vegetable_oils"]:
        for m in months:
            solution[f"store_{oil}_{m}"] = float(variables[f"store_{oil}_{m}"].X)

    # 4) y variables
    for oil in data["vegetable_oils"]:
        for m in months:
            solution[f"y_{oil}_{m}"] = float(variables[f"y_{oil}_{m}"].X)
    for oil in data["non_vegetable_oils"]:
        for m in months:
            solution[f"y_{oil}_{m}"] = float(variables[f"y_{oil}_{m}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }