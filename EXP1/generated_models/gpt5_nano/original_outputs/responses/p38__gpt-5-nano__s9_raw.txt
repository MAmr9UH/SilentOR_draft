import gurobipy as gp

def build_model(data: dict):
    """
    Build and return the GUROBI model and a flat dictionary of all decision variables.
    The model contains:
    - Production: prod_I_t, prod_II_t for t in months
    - Inventory: inv_I_t, inv_II_t for t in months
    - Storage: own_storage_t, external_storage_t for t in months
    - Balance constraints, capacity constraints, and storage-volume linkage
    - Objective: minimize production cost + storage cost
    """
    model = gp.Model()

    months = list(data["months"])
    initial_I = data["initial_inventory"]["I"]
    initial_II = data["initial_inventory"]["II"]
    demand_I = {m: data["demand"]["I"][str(m)] for m in months}
    demand_II = {m: data["demand"]["II"][str(m)] for m in months}
    cap = data["monthly_total_production_capacity"]
    own_cap = data["own_warehouse_capacity_cubic_m"]
    vol = data["unit_volume"]  # {'I': 0.2, 'II': 0.4}
    cost_I = data["production_cost"]["I"]
    cost_II = data["production_cost"]["II"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    # Create flat variable dictionary
    var_by_key = {}

    for m in months:
        key_prod_I = f"prod_I_{m}"
        key_prod_II = f"prod_II_{m}"
        key_inv_I = f"inv_I_{m}"
        key_inv_II = f"inv_II_{m}"
        key_own = f"own_storage_{m}"
        key_ext = f"external_storage_{m}"

        var_by_key[key_prod_I] = model.addVar(lb=0.0, name=key_prod_I)
        var_by_key[key_prod_II] = model.addVar(lb=0.0, name=key_prod_II)
        var_by_key[key_inv_I] = model.addVar(lb=0.0, name=key_inv_I)
        var_by_key[key_inv_II] = model.addVar(lb=0.0, name=key_inv_II)
        var_by_key[key_own] = model.addVar(lb=0.0, name=key_own)
        var_by_key[key_ext] = model.addVar(lb=0.0, name=key_ext)

    # Constraints

    # 1) Monthly production capacity: prod_I_t + prod_II_t <= capacity
    for m in months:
        model.addConstr(var_by_key[f"prod_I_{m}"] + var_by_key[f"prod_II_{m}"] <= cap)

    # 2) Inventory balance equations
    # I
    for idx, m in enumerate(months):
        invI = var_by_key[f"inv_I_{m}"]
        prodI = var_by_key[f"prod_I_{m}"]
        dI = demand_I[m]
        if idx == 0:
            # July: previous inventory is initial_I
            model.addConstr(invI == initial_I + prodI - dI)
        else:
            prev_inv = var_by_key[f"inv_I_{months[idx-1]}"]
            model.addConstr(invI == prev_inv + prodI - dI)

    # II
    for idx, m in enumerate(months):
        invII = var_by_key[f"inv_II_{m}"]
        prodII = var_by_key[f"prod_II_{m}"]
        dII = demand_II[m]
        if idx == 0:
            model.addConstr(invII == initial_II + prodII - dII)
        else:
            prev_inv = var_by_key[f"inv_II_{months[idx-1]}"]
            model.addConstr(invII == prev_inv + prodII - dII)

    # 3) Storage balance: total inventory volume equals storage installed
    for m in months:
        invI_vol = vol["I"] * var_by_key[f"inv_I_{m}"]
        invII_vol = vol["II"] * var_by_key[f"inv_II_{m}"]
        total_vol = invI_vol + invII_vol
        model.addConstr(total_vol == var_by_key[f"own_storage_{m}"] + var_by_key[f"external_storage_{m}"])

        # 4) Own storage capacity constraint
        model.addConstr(var_by_key[f"own_storage_{m}"] <= own_cap)

    # 5) Nonnegativity is enforced by lb=0 for all variables (already set)

    # Objective: minimize production costs + storage costs
    objective = gp.quicksum(
        var_by_key[f"prod_I_{m}"] * cost_I for m in months
    ) + gp.quicksum(
        var_by_key[f"prod_II_{m}"] * cost_II for m in months
    ) + gp.quicksum(
        var_by_key[f"own_storage_{m}"] * own_cost for m in months
    ) + gp.quicksum(
        var_by_key[f"external_storage_{m}"] * ext_cost for m in months
    )

    model.setObjective(objective, sense=gp.GRB.MINIMIZE)

    # Prepare the output variable container with exactly the requested keys
    variables = {}
    for m in months:
        variables[f"prod_I_{m}"] = var_by_key[f"prod_I_{m}"]
    for m in months:
        variables[f"prod_II_{m}"] = var_by_key[f"prod_II_{m}"]
    for m in months:
        variables[f"inv_I_{m}"] = var_by_key[f"inv_I_{m}"]
    for m in months:
        variables[f"inv_II_{m}"] = var_by_key[f"inv_II_{m}"]
    for m in months:
        variables[f"own_storage_{m}"] = var_by_key[f"own_storage_{m}"]
    for m in months:
        variables[f"external_storage_{m}"] = var_by_key[f"external_storage_{m}"]

    return model, variables


def solve(data: dict) -> dict:
    """
    Build, optimize, and return the solution in the required schema.
    """
    # Build model (no optimization yet)
    model, variables = build_model(data)

    # Optimize
    model.optimize()

    # Status string
    status = model.Status
    status_str_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_str_map.get(status, str(status))

    # Objective value
    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dict with required keys in the specified order
    months = list(data["months"])
    solution = {}

    # prod_I_7 .. prod_I_12
    for m in months:
        solution[f"prod_I_{m}"] = float(variables[f"prod_I_{m}"].X)

    # prod_II_7 .. prod_II_12
    for m in months:
        solution[f"prod_II_{m}"] = float(variables[f"prod_II_{m}"].X)

    # inv_I_7 .. inv_I_12
    for m in months:
        solution[f"inv_I_{m}"] = float(variables[f"inv_I_{m}"].X)

    # inv_II_7 .. inv_II_12
    for m in months:
        solution[f"inv_II_{m}"] = float(variables[f"inv_II_{m}"].X)

    # own_storage_7 .. own_storage_12
    for m in months:
        solution[f"own_storage_{m}"] = float(variables[f"own_storage_{m}"].X)

    # external_storage_7 .. external_storage_12
    for m in months:
        solution[f"external_storage_{m}"] = float(variables[f"external_storage_{m}"].X)

    return {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {"type": "string"},
            "objective": {"type": "number", "description": "minimum total production and inventory cost"},
            "solution": {
                "type": "object",
                "required": [
                    "prod_I_7","prod_I_8","prod_I_9","prod_I_10","prod_I_11","prod_I_12",
                    "prod_II_7","prod_II_8","prod_II_9","prod_II_10","prod_II_11","prod_II_12",
                    "inv_I_7","inv_I_8","inv_I_9","inv_I_10","inv_I_11","inv_I_12",
                    "inv_II_7","inv_II_8","inv_II_9","inv_II_10","inv_II_11","inv_II_12",
                    "own_storage_7","own_storage_8","own_storage_9","own_storage_10","own_storage_11","own_storage_12",
                    "external_storage_7","external_storage_8","external_storage_9","external_storage_10","external_storage_11","external_storage_12"
                ],
                "properties": {  # numeric values for each key
                    **{f"prod_I_{m}": {"type": "number"} for m in months},
                    **{f"prod_II_{m}": {"type": "number"} for m in months},
                    **{f"inv_I_{m}": {"type": "number"} for m in months},
                    **{f"inv_II_{m}": {"type": "number"} for m in months},
                    **{f"own_storage_{m}": {"type": "number"} for m in months},
                    **{f"external_storage_{m}": {"type": "number"} for m in months},
                }
            }
        },
        "objective": obj_val,
        "status": status_str,
        "solution": solution
    }