import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    months = data["months"]
    first_month = min(months)
    last_month = max(months)

    model = gp.Model()

    # Parameters from data
    vol_I = data["unit_volume"]["I"]
    vol_II = data["unit_volume"]["II"]
    cap_prod = data["monthly_total_production_capacity"]
    own_cap = data["own_warehouse_capacity_cubic_m"]
    cost_I = data["production_cost"]["I"]
    cost_II = data["production_cost"]["II"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    # Demands indexed by month
    demand_I = {m: data["demand"]["I"][str(m)] for m in months}
    demand_II = {m: data["demand"]["II"][str(m)] for m in months}

    # Initial inventories
    init_I = data["initial_inventory"]["I"]
    init_II = data["initial_inventory"]["II"]

    # Create variables
    variables = {}

    for m in months:
        key = f"prod_I_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

        key = f"prod_II_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

        key = f"inv_I_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

        key = f"inv_II_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

        key = f"own_storage_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

        key = f"external_storage_{m}"
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=key)
        variables[key] = v

    model.update()

    # Balance constraints
    for m in months:
        if m == first_month:
            # inv_I_m = init_I + prod_I_m - demand_I_m
            model.addConstr(variables[f"inv_I_{m}"] == init_I + variables[f"prod_I_{m}"] - demand_I[m])
            model.addConstr(variables[f"inv_II_{m}"] == init_II + variables[f"prod_II_{m}"] - demand_II[m])
        else:
            model.addConstr(variables[f"inv_I_{m}"] == variables[f"inv_I_{m-1}"] + variables[f"prod_I_{m}"] - demand_I[m])
            model.addConstr(variables[f"inv_II_{m}"] == variables[f"inv_II_{m-1}"] + variables[f"prod_II_{m}"] - demand_II[m])

        # Storage balance: total storage volume equals end-of-month inventory volume
        total_vol = variables[f"inv_I_{m}"] * vol_I + variables[f"inv_II_{m}"] * vol_II
        model.addConstr(variables[f"own_storage_{m}"] + variables[f"external_storage_{m}"] == total_vol)

        # Storage capacity for own warehouse
        model.addConstr(variables[f"own_storage_{m}"] <= own_cap)

        # Production capacity per month
        model.addConstr(variables[f"prod_I_{m}"] + variables[f"prod_II_{m}"] <= cap_prod)

    # Objective: minimize production costs + storage costs
    objective = gp.LinExpr()
    for m in months:
        objective += variables[f"prod_I_{m}"] * cost_I
        objective += variables[f"prod_II_{m}"] * cost_II
        objective += variables[f"own_storage_{m}"] * own_cost
        objective += variables[f"external_storage_{m}"] * ext_cost

    model.setObjective(objective, GRB.MINIMIZE)

    model.update()
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
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))

    # Objective value
    obj_val = float(model.ObjVal)

    # Ensure variables are updated before reading
    model.update()

    solution = {}
    for key in sorted(variables.keys()):
        solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": obj_val,
        "solution": solution
    }