import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    # Data extraction
    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]
    oils = veg_oils + nonveg_oils
    months = data["months"]
    
    sell_price = data["sell_price"]
    purchase_price = data["purchase_price"]  # purchase_price[month][oil]
    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    hardness = data["hardness"]  # hardness[oil]
    min_hard = data["min_hardness"]
    max_hard = data["max_hardness"]
    initial_storage = data["initial_storage_per_oil"]
    final_storage = data["required_final_storage_per_oil"]
    veg_refine_cap = data["veg_refine_cap"]
    nonveg_refine_cap = data["nonveg_refine_cap"]
    
    M = 10**6  # big-M
    
    # Decision variables
    V = {}  # buy_{oil}_{month}
    U = {}  # use_{oil}_{month}
    S = {}  # store_{oil}_{month}
    Y = {}  # y_{oil}_{month}
    
    for oil in oils:
        for m in months:
            key_buy = f"buy_{oil}_{m}"
            V[key_buy] = model.addVar(vtype=GRB.CONTINUOUS, name=key_buy)
            
            key_use = f"use_{oil}_{m}"
            U[key_use] = model.addVar(vtype=GRB.CONTINUOUS, name=key_use)
            
            key_store = f"store_{oil}_{m}"
            S[key_store] = model.addVar(vtype=GRB.CONTINUOUS, name=key_store)
            
            key_y = f"y_{oil}_{m}"
            Y[key_y] = model.addVar(vtype=GRB.BINARY, name=key_y)
    
    model.update()
    
    # Objective: max revenue minus purchases minus storage costs
    revenue = gp.quicksum(sell_price * U[f"use_{oil}_{m}"] for oil in oils for m in months)
    purchase_cost = gp.quicksum(purchase_price[m][oil] * V[f"buy_{oil}_{m}"] for oil in oils for m in months)
    storage_cost_expr = gp.quicksum(storage_cost * S[f"store_{oil}_{m}"] for oil in oils for m in months)
    model.setObjective(revenue - purchase_cost - storage_cost_expr, GRB.MAXIMIZE)
    
    # Constraints
    
    # 1) Refining capacity per month
    for m in months:
        veg_usage = gp.quicksum(U[f"use_{oil}_{m}"] for oil in veg_oils)
        nonveg_usage = gp.quicksum(U[f"use_{oil}_{m}"] for oil in nonveg_oils)
        model.addConstr(veg_usage <= veg_refine_cap, name=f"veg_cap_{m}")
        model.addConstr(nonveg_usage <= nonveg_refine_cap, name=f"nonveg_cap_{m}")
    
    # 2) Hardness blending: 3 <= weighted hardness <= 6 for each month
    for m in months:
        total_use = gp.quicksum(U[f"use_{oil}_{m}"] for oil in oils)
        total_hard = gp.quicksum(hardness[oil] * U[f"use_{oil}_{m}"] for oil in oils)
        model.addConstr(total_hard >= min_hard * total_use, name=f"min_hard_{m}")
        model.addConstr(total_hard <= max_hard * total_use, name=f"max_hard_{m}")
    
    # 3) At most three oils used per month (based on y variables)
    for m in months:
        model.addConstr(gp.quicksum(Y[f"y_{oil}_{m}"] for oil in oils) <= 3, name=f"max3_oils_{m}")
    
    # 4) If oil is used, at least 20 tons; and if not used, usage 0 (via big-M)
    for oil in oils:
        for m in months:
            model.addConstr(U[f"use_{oil}_{m}"] <= M * Y[f"y_{oil}_{m}"])
            model.addConstr(U[f"use_{oil}_{m}"] >= 20 * Y[f"y_{oil}_{m}"])
    
    # 5) VEG1/VEG2 => OIL3 must be used that month
    for m in months:
        model.addConstr(Y[f"y_VEG1_{m}"] <= Y[f"y_OIL3_{m}"])
        model.addConstr(Y[f"y_VEG2_{m}"] <= Y[f"y_OIL3_{m}"])
    
    # 6) Storage balance and storage caps
    # Jan starts with initial_storage
    for oil in oils:
        # Jan balance
        key_store_jan = f"store_{oil}_Jan"
        key_buy_jan = f"buy_{oil}_Jan"
        key_use_jan = f"use_{oil}_Jan"
        model.addConstr(S[key_store_jan] == initial_storage + V[key_buy_jan] - U[key_use_jan], name=f"bal_Jan_{oil}")
        # Storage cap
        model.addConstr(S[key_store_jan] >= 0, name=f"stockneg_Jan_{oil}")
        model.addConstr(S[key_store_jan] <= storage_cap, name=f"stockcap_Jan_{oil}")
    
        # Feb-Jun balances
        for idx in range(1, len(months)):
            m = months[idx]
            prev_m = months[idx-1]
            key_store = f"store_{oil}_{m}"
            key_store_prev = f"store_{oil}_{prev_m}"
            key_buy = f"buy_{oil}_{m}"
            key_use = f"use_{oil}_{m}"
            model.addConstr(S[key_store] == S[key_store_prev] + V[key_buy] - U[key_use], name=f"bal_{oil}_{m}")
            model.addConstr(S[key_store] >= 0, name=f"stockneg_{oil}_{m}")
            model.addConstr(S[key_store] <= storage_cap, name=f"stockcap_{oil}_{m}")
    
        # Final storage end of Jun must be final_storage
        key_store_jun = f"store_{oil}_Jun"
        model.addConstr(S[key_store_jun] == final_storage, name=f"final_store_{oil}")
    
    model.update()
    return model, V  # Return the model and the dictionary of variables (as required)

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    # Status string
    stat = model.Status
    status_str = "UNKNOWN"
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)
    
    # Objective value
    obj_val = float(model.ObjVal) if model.ObjVal is not None else None
    
    # Build solution dictionary with all variable values
    solution = {}
    oils = data["vegetable_oils"] + data["non_vegetable_oils"]
    months = data["months"]
    for oil in oils:
        for m in months:
            for t in ["buy", "use", "store", "y"]:
                key = f"{t}_{oil}_{m}"
                # Some keys might not exist if misnamed; guard
                if key in variables:
                    solution[key] = float(variables[key].X)
                else:
                    # In case of any mismatch, set 0.0 to maintain schema integrity
                    solution[key] = 0.0
    
    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }