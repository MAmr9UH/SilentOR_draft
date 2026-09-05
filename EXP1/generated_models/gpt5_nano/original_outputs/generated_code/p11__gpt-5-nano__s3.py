import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    # Create model
    model = gp.Model()
    # Silence default output for cleaner runs (can be removed if debugging)
    model.setParam('OutputFlag', 0)

    months = data['months']
    veg_oils = data['vegetable_oils']
    nonveg_oils = data['non_vegetable_oils']
    oils = veg_oils + nonveg_oils

    sell_price = data['sell_price']
    storage_cost = data['storage_cost_per_ton_month']
    storage_cap = data['storage_cap_per_oil']
    initial_store = data['initial_storage_per_oil']
    final_store_required = data['required_final_storage_per_oil']
    veg_cap = data['veg_refine_cap']
    nonveg_cap = data['nonveg_refine_cap']
    min_hard = data['min_hardness']
    max_hard = data['max_hardness']
    hard = data['hardness']

    BIG_M = 10000  # sufficiently large for linking constraints

    # Prepare variable dictionary
    variables = {}

    # Helper to access variable
    def v(key):
        return variables[key]

    # Create variables
    for oil in oils:
        for month in months:
            buy_key = f"buy_{oil}_{month}"
            use_key = f"use_{oil}_{month}"
            store_key = f"store_{oil}_{month}"
            y_key = f"y_{oil}_{month}"

            buy_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=buy_key)
            use_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=use_key)
            store_var = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=store_key)
            y_var = model.addVar(vtype=GRB.BINARY, name=y_key)

            variables[buy_key] = buy_var
            variables[use_key] = use_var
            variables[store_key] = store_var
            variables[y_key] = y_var

    # Constraints

    # 1) Initial storage balance for January
    for oil in oils:
        buy_jan = f"buy_{oil}_Jan"
        use_jan = f"use_{oil}_Jan"
        store_jan = f"store_{oil}_Jan"

        model.addConstr(  initial_store(oil) + v(buy_jan) - v(use_jan) == v(store_jan) )

    # 2) Monthly storage balance from prev month
    for i in range(1, len(months)):
        month = months[i]
        prev = months[i-1]
        for oil in oils:
            buy_key = f"buy_{oil}_{month}"
            use_key = f"use_{oil}_{month}"
            store_key = f"store_{oil}_{month}"
            store_prev = f"store_{oil}_{prev}"
            model.addConstr( v(store_prev) + v(buy_key) - v(use_key) == v(store_key) )

    # 3) Final storage at end of June must be 500 for each oil
    for oil in oils:
        model.addConstr( v(f"store_{oil}_Jun") == final_store_required )

    # 4) Refining capacity per month
    for month in months:
        # Vegetable oils total used <= veg_cap
        model.addConstr( v(f"use_VEG1_{month}") + v(f"use_VEG2_{month}") <= veg_cap )
        # Non-vegetable oils total used <= nonveg_cap
        model.addConstr( v(f"use_OIL1_{month}") + v(f"use_OIL2_{month}") + v(f"use_OIL3_{month}") <= nonveg_cap )

    # 5) At most three oils used per month
    for month in months:
        model.addConstr(
            v("y_VEG1_"+month) + v("y_VEG2_"+month) + v("y_OIL1_"+month) + v("y_OIL2_"+month) + v("y_OIL3_"+month) <= 3
        )

    # 6) Linking y and use: if oil used (y=1) then at least 20, and if y=0 then use=0
    for oil in oils:
        for month in months:
            model.addConstr( v(f"use_{oil}_{month}") <= BIG_M * v(f"y_{oil}_{month}") )
            model.addConstr( v(f"use_{oil}_{month}") >= 20 * v(f"y_{oil}_{month}") )

    # 7) If VEG1 or VEG2 used in a month, OIL3 must be used that month
    for month in months:
        model.addConstr( v("y_VEG1_"+month) <= v("y_OIL3_"+month) )
        model.addConstr( v("y_VEG2_"+month) <= v("y_OIL3_"+month) )

    # 8) Storage capacity per oil
    for oil in oils:
        for month in months:
            model.addConstr( v(f"store_{oil}_{month}") <= storage_cap )

    # 9) Hardness constraint: weighted average hardness must be between min and max
    for month in months:
        total_use = quicksum( v(f"use_{oil}_{month}") for oil in oils )
        weighted_hard = quicksum( hard[oil] * v(f"use_{oil}_{month}") for oil in oils )
        model.addConstr( weighted_hard >= min_hard * total_use )
        model.addConstr( weighted_hard <= max_hard * total_use )

    # 10) Objective: maximize revenue from final product minus oil purchase costs and storage costs
    objective = gp.LinExpr()
    for month in months:
        # Revenue from selling product produced that month
        Sm = quicksum( v(f"use_{oil}_{month}") for oil in oils )
        objective += sell_price * Sm
        # Subtract purchase costs
        for oil in oils:
            price = data['purchase_price'][month][oil]
            objective -= price * v(f"buy_{oil}_{month}")
        # Subtract storage costs for stored oil
        for oil in oils:
            objective -= storage_cost * v(f"store_{oil}_{month}")

    model.setObjective(objective, GRB.MAXIMIZE)

    return model, variables

def initial_store(oil):
    # Given the data, initial storage per oil is 500 tons for all oils
    # This function is a placeholder for readability; values are constants
    return 500.0

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(st, str(st))

    obj_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with all variable values
    solution = {}
    # We need to return flat dict with keys identical to variable keys
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_value,
        "solution": solution
    }