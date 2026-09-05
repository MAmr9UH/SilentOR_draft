import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()

    months = data["months"]
    cap = data["monthly_total_production_capacity"]
    vol_I = data["unit_volume"]["I"]
    vol_II = data["unit_volume"]["II"]
    demand_I = {}
    demand_II = {}
    for m in months:
        demand_I[m] = data["demand"]["I"][str(m)]
        demand_II[m] = data["demand"]["II"][str(m)]
    prod_cost_I = data["production_cost"]["I"]
    prod_cost_II = data["production_cost"]["II"]
    own_cap = data["own_warehouse_capacity_cubic_m"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    # Decision variables (flat)
    prod_I = {}
    prod_II = {}
    inv_I = {}
    inv_II = {}
    own_storage = {}
    external_storage = {}

    for m in months:
        prod_I[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"prod_I_{m}")
        prod_II[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"prod_II_{m}")
        inv_I[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"inv_I_{m}")
        inv_II[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"inv_II_{m}")
        own_storage[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"own_storage_{m}")
        external_storage[m] = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"external_storage_{m}")

    model.update()

    # Inventory balance
    for idx, m in enumerate(months):
        if idx == 0:
            model.addConstr(inv_I[m] == prod_I[m] - demand_I[m])
            model.addConstr(inv_II[m] == prod_II[m] - demand_II[m])
        else:
            prev_m = months[idx - 1]
            model.addConstr(inv_I[m] == inv_I[prev_m] + prod_I[m] - demand_I[m])
            model.addConstr(inv_II[m] == inv_II[prev_m] + prod_II[m] - demand_II[m])

    # Production capacity per month
    for m in months:
        model.addConstr(prod_I[m] + prod_II[m] <= cap)

    # Storage balance and capacity
    for m in months:
        vol = inv_I[m] * vol_I + inv_II[m] * vol_II
        model.addConstr(vol == own_storage[m] + external_storage[m])
        model.addConstr(own_storage[m] <= own_cap)

    # Objective
    obj = gp.quicksum(prod_I[m] * prod_cost_I for m in months) \
        + gp.quicksum(prod_II[m] * prod_cost_II for m in months) \
        + gp.quicksum(own_storage[m] * own_cost for m in months) \
        + gp.quicksum(external_storage[m] * ext_cost for m in months)

    model.setObjective(obj, gp.GRB.MINIMIZE)

    # Assemble variable dictionary with exact keys
    variables = {
        "prod_I_7": prod_I[7], "prod_I_8": prod_I[8], "prod_I_9": prod_I[9], "prod_I_10": prod_I[10], "prod_I_11": prod_I[11], "prod_I_12": prod_I[12],
        "prod_II_7": prod_II[7], "prod_II_8": prod_II[8], "prod_II_9": prod_II[9], "prod_II_10": prod_II[10], "prod_II_11": prod_II[11], "prod_II_12": prod_II[12],
        "inv_I_7": inv_I[7], "inv_I_8": inv_I[8], "inv_I_9": inv_I[9], "inv_I_10": inv_I[10], "inv_I_11": inv_I[11], "inv_I_12": inv_I[12],
        "inv_II_7": inv_II[7], "inv_II_8": inv_II[8], "inv_II_9": inv_II[9], "inv_II_10": inv_II[10], "inv_II_11": inv_II[11], "inv_II_12": inv_II[12],
        "own_storage_7": own_storage[7], "own_storage_8": own_storage[8], "own_storage_9": own_storage[9], "own_storage_10": own_storage[10], "own_storage_11": own_storage[11], "own_storage_12": own_storage[12],
        "external_storage_7": external_storage[7], "external_storage_8": external_storage[8], "external_storage_9": external_storage[9], "external_storage_10": external_storage[10], "external_storage_11": external_storage[11], "external_storage_12": external_storage[12]
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status to string
    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.CUTOFF: "CUTOFF",
    }
    status_str = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }