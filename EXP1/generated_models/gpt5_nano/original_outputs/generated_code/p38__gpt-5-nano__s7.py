from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    # Extract data
    months = data.get("months", [])
    demand = data.get("demand", {})
    demand_I = {int(k): int(v) for k, v in demand.get("I", {}).items()}
    demand_II = {int(k): int(v) for k, v in demand.get("II", {}).items()}
    cost_I = float(data.get("production_cost", {}).get("I", 0.0))
    cost_II = float(data.get("production_cost", {}).get("II", 0.0))
    monthly_capacity = float(data.get("monthly_total_production_capacity", 0.0))
    unit_vol_I = float(data.get("unit_volume", {}).get("I", 0.0))
    unit_vol_II = float(data.get("unit_volume", {}).get("II", 0.0))
    own_capacity = float(data.get("own_warehouse_capacity_cubic_m", 0.0))
    own_cost = float(data.get("own_storage_cost_per_cubic_m_month", 0.0))
    external_cost = float(data.get("external_storage_cost_per_cubic_m_month", 0.0))

    model = Model()

    # Prepare variable container
    variables = {}

    # Create decision variables
    for t in months:
        # Production
        key_prod_I = f"prod_I_{t}"
        var_prod_I = model.addVar(lb=0.0, name=key_prod_I)
        variables[key_prod_I] = var_prod_I

        key_prod_II = f"prod_II_{t}"
        var_prod_II = model.addVar(lb=0.0, name=key_prod_II)
        variables[key_prod_II] = var_prod_II

        # Inventory at end of month
        key_inv_I = f"inv_I_{t}"
        var_inv_I = model.addVar(lb=0.0, name=key_inv_I)
        variables[key_inv_I] = var_inv_I

        key_inv_II = f"inv_II_{t}"
        var_inv_II = model.addVar(lb=0.0, name=key_inv_II)
        variables[key_inv_II] = var_inv_II

        # Storage choices
        key_own = f"own_storage_{t}"
        var_own = model.addVar(lb=0.0, name=key_own)
        variables[key_own] = var_own

        key_ext = f"external_storage_{t}"
        var_ext = model.addVar(lb=0.0, name=key_ext)
        variables[key_ext] = var_ext

    model.update()

    # Demand balance constraints
    for t in months:
        if t == months[0]:
            # inv_I_7 = prod_I_7 - demand_I_7
            model.addConstr(variables[f"inv_I_{t}"] == variables[f"prod_I_{t}"] - demand_I.get(t, 0))
            model.addConstr(variables[f"inv_II_{t}"] == variables[f"prod_II_{t}"] - demand_II.get(t, 0))
        else:
            model.addConstr(variables[f"inv_I_{t}"] == variables[f"inv_I_{t-1}"] + variables[f"prod_I_{t}"] - demand_I.get(t, 0))
            model.addConstr(variables[f"inv_II_{t}"] == variables[f"inv_II_{t-1}"] + variables[f"prod_II_{t}"] - demand_II.get(t, 0))

    # Capacity constraints
    for t in months:
        model.addConstr(variables[f"prod_I_{t}"] + variables[f"prod_II_{t}"] <= monthly_capacity)

    # Storage balance and capacity
    for t in months:
        volume_t = variables[f"inv_I_{t}"] * unit_vol_I + variables[f"inv_II_{t}"] * unit_vol_II
        model.addConstr(variables[f"own_storage_{t}"] + variables[f"external_storage_{t}"] == volume_t)
        model.addConstr(variables[f"own_storage_{t}"] <= own_capacity)

    # Objective: minimize production + storage costs
    prod_cost = quicksum(variables[f"prod_I_{t}"] * cost_I + variables[f"prod_II_{t}"] * cost_II for t in months)
    storage_cost = quicksum(variables[f"own_storage_{t}"] * own_cost + variables[f"external_storage_{t}"] * external_cost for t in months)
    model.setObjective(prod_cost + storage_cost, GRB.MINIMIZE)

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, "UNKNOWN")

    # Objective value
    objective_value = float(model.ObjVal)

    # Build solution dict with required keys in deterministic order
    solution_keys = [
        "prod_I_7","prod_I_8","prod_I_9","prod_I_10","prod_I_11","prod_I_12",
        "prod_II_7","prod_II_8","prod_II_9","prod_II_10","prod_II_11","prod_II_12",
        "inv_I_7","inv_I_8","inv_I_9","inv_I_10","inv_I_11","inv_I_12",
        "inv_II_7","inv_II_8","inv_II_9","inv_II_10","inv_II_11","inv_II_12",
        "own_storage_7","own_storage_8","own_storage_9","own_storage_10","own_storage_11","own_storage_12",
        "external_storage_7","external_storage_8","external_storage_9","external_storage_10","external_storage_11","external_storage_12"
    ]
    solution = {}
    for key in solution_keys:
        var = variables[key]
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }