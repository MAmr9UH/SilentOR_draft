import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()
    model.setParam('OutputFlag', 0)

    # Data extraction
    oils = data["vegetable_oils"] + data["non_vegetable_oils"]
    months = data["months"]

    initial_store = data["initial_storage_per_oil"]
    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    min_hard = data["min_hardness"]
    max_hard = data["max_hardness"]
    sell_price = data["sell_price"]
    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]
    hardness = data["hardness"]
    required_final_storage = data["required_final_storage_per_oil"]

    # Price dictionary
    purchase_price = data["purchase_price"]
    price = {}
    for m in months:
        for o in oils:
            price[(o, m)] = purchase_price[m][o]

    # Big-M
    BIGM = 10000

    # Decision variables
    buy = {}
    use = {}
    store = {}
    y = {}

    for o in oils:
        for m in months:
            buy[(o, m)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"buy_{o}_{m}")
            use[(o, m)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"use_{o}_{m}")
            store[(o, m)] = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name=f"store_{o}_{m}")
            y[(o, m)] = model.addVar(lb=0, ub=1, vtype=GRB.BINARY, name=f"y_{o}_{m}")

    model.update()

    # Objective: maximize revenue from final product minus purchases minus storage costs
    revenue = gp.quicksum(use[(o, m)] * sell_price for o in oils for m in months)
    purchase_cost = gp.quicksum(buy[(o, m)] * price[(o, m)] for o in oils for m in months)
    storage_cost_term = gp.quicksum(store[(o, m)] * storage_cost for o in oils for m in months)

    model.setObjective(revenue - purchase_cost - storage_cost_term, GRB.MAXIMIZE)

    # Constraints

    # 1) Inventory balance and storage capacity
    for o in oils:
        for idx, m in enumerate(months):
            if idx == 0:
                model.addConstr(store[(o, m)] == initial_store + buy[(o, m)] - use[(o, m)])
            else:
                prev_m = months[idx - 1]
                model.addConstr(store[(o, m)] == store[(o, prev_m)] + buy[(o, m)] - use[(o, m)])

            model.addConstr(store[(o, m)] <= storage_cap)

    # End of June storage requirements
    for o in oils:
        model.addConstr(store[(o, 'Jun')] == required_final_storage)

    # 2) Refining capacity per month
    for m in months:
        veg_sum = gp.quicksum(use[(o, m)] for o in data["vegetable_oils"])
        nonveg_sum = gp.quicksum(use[(o, m)] for o in data["non_vegetable_oils"])
        model.addConstr(veg_sum <= veg_cap)
        model.addConstr(nonveg_sum <= nonveg_cap)

    # 3) Usage and binary linkage
    for o in oils:
        for m in months:
            model.addConstr(use[(o, m)] <= BIGM * y[(o, m)])
            model.addConstr(use[(o, m)] >= 20 * y[(o, m)])

    # 4) At most three oils used per month
    for m in months:
        model.addConstr(gp.quicksum(y[(o, m)] for o in oils) <= 3)

    # 5) VEG1/VEG2 require OIL3 if used
    for m in months:
        model.addConstr(y[('VEG1', m)] <= y[('OIL3', m)])
        model.addConstr(y[('VEG2', m)] <= y[('OIL3', m)])

    # 6) Hardness constraints (blend hardness)
    for m in months:
        total_use = gp.quicksum(use[(o, m)] for o in oils)
        weighted_hard = gp.quicksum(hardness[o] * use[(o, m)] for o in oils)
        model.addConstr(weighted_hard <= max_hard * total_use)
        model.addConstr(weighted_hard >= min_hard * total_use)

    # Prepare solution variable mapping
    variables = {}
    for o in oils:
        for m in months:
            variables[f"buy_{o}_{m}"] = buy[(o, m)]
            variables[f"use_{o}_{m}"] = use[(o, m)]
            variables[f"store_{o}_{m}"] = store[(o, m)]
            variables[f"y_{o}_{m}"] = y[(o, m)]

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    # Objective value
    objective = float(model.ObjVal)

    # Build solution dict
    solution = {}
    months = data["months"]
    oils = data["vegetable_oils"] + data["non_vegetable_oils"]
    for o in oils:
        for m in months:
            solution[f"buy_{o}_{m}"] = float(variables[f"buy_{o}_{m}"].X)
            solution[f"use_{o}_{m}"] = float(variables[f"use_{o}_{m}"].X)
            solution[f"store_{o}_{m}"] = float(variables[f"store_{o}_{m}"].X)
            solution[f"y_{o}_{m}"] = float(variables[f"y_{o}_{m}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }