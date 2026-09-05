import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    months = data["months"]
    model = gp.Model()

    # Containers for variables
    variables = {}

    prod_I = {}
    prod_II = {}
    inv_I = {}
    inv_II = {}
    own_storage = {}
    external_storage = {}

    # Create variables
    for m in months:
        key = f"prod_I_{m}"
        prod_I[m] = model.addVar(lb=0.0, name=key)
        variables[key] = prod_I[m]

        key = f"prod_II_{m}"
        prod_II[m] = model.addVar(lb=0.0, name=key)
        variables[key] = prod_II[m]

        key = f"inv_I_{m}"
        inv_I[m] = model.addVar(lb=0.0, name=key)
        variables[key] = inv_I[m]

        key = f"inv_II_{m}"
        inv_II[m] = model.addVar(lb=0.0, name=key)
        variables[key] = inv_II[m]

        key = f"own_storage_{m}"
        own_storage[m] = model.addVar(lb=0.0, name=key)
        variables[key] = own_storage[m]

        key = f"external_storage_{m}"
        external_storage[m] = model.addVar(lb=0.0, name=key)
        variables[key] = external_storage[m]

    # Objective: production cost + storage cost
    prod_cost_I = data["production_cost"]["I"]
    prod_cost_II = data["production_cost"]["II"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    obj = gp.quicksum(prod_cost_I * prod_I[m] + prod_cost_II * prod_II[m] for m in months) \
          + gp.quicksum(own_cost * own_storage[m] + ext_cost * external_storage[m] for m in months)
    model.setObjective(obj, GRB.MINIMIZE)

    # Demand and balance constraints
    demand_I = data["demand"]["I"]
    demand_II = data["demand"]["II"]

    for idx, m in enumerate(months):
        dI = demand_I[str(m)]
        dII = demand_II[str(m)]

        if idx == 0:
            model.addConstr(inv_I[m] == prod_I[m] - dI)
            model.addConstr(inv_II[m] == prod_II[m] - dII)
        else:
            prev = months[idx - 1]
            model.addConstr(inv_I[m] == inv_I[prev] + prod_I[m] - dI)
            model.addConstr(inv_II[m] == inv_II[prev] + prod_II[m] - dII)

        # Storage balance: own + external storage must equal inventory volume
        model.addConstr(own_storage[m] + external_storage[m] == 0.2 * inv_I[m] + 0.4 * inv_II[m])

        # Own storage capacity
        model.addConstr(own_storage[m] <= data["own_warehouse_capacity_cubic_m"])

        # Production capacity per month
        model.addConstr(prod_I[m] + prod_II[m] <= data["monthly_total_production_capacity"])

        # Non-negativity is ensured by lb=0 for all variables

    model.update()
    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_num = model.Status
    if status_num == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_num == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_num == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_num == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_num == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_num)

    objective = float(model.ObjVal)

    # Build solution dictionary with all required keys
    solution = {}
    months = data["months"]

    for m in months:
        solution[f"prod_I_{m}"] = float(variables[f"prod_I_{m}"].X)
        solution[f"prod_II_{m}"] = float(variables[f"prod_II_{m}"].X)
        solution[f"inv_I_{m}"] = float(variables[f"inv_I_{m}"].X)
        solution[f"inv_II_{m}"] = float(variables[f"inv_II_{m}"].X)
        solution[f"own_storage_{m}"] = float(variables[f"own_storage_{m}"].X)
        solution[f"external_storage_{m}"] = float(variables[f"external_storage_{m}"].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }