import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    months = data["months"]
    unit_vol_I = data["unit_volume"]["I"]
    unit_vol_II = data["unit_volume"]["II"]

    # Decision variables
    prod_I = {}
    prod_II = {}
    inv_I = {}
    inv_II = {}
    own_storage = {}
    external_storage = {}

    for m in months:
        prod_I[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_I_{m}")
        prod_II[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_II_{m}")
        inv_I[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_I_{m}")
        inv_II[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_II_{m}")
        own_storage[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"own_storage_{m}")
        external_storage[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"external_storage_{m}")

    model.update()

    # Parameters
    initial_I = data["initial_inventory"]["I"]
    demand_I = data["demand"]["I"]
    demand_II = data["demand"]["II"]
    capacity = data["monthly_total_production_capacity"]
    own_capacity = data["own_warehouse_capacity_cubic_m"]
    own_storage_cost = data["own_storage_cost_per_cubic_m_month"]
    external_storage_cost = data["external_storage_cost_per_cubic_m_month"]
    prod_cost_I = data["production_cost"]["I"]
    prod_cost_II = data["production_cost"]["II"]

    # Balance constraints
    for idx, m in enumerate(months):
        dI = demand_I[str(m)]
        if m == months[0]:
            model.addConstr(inv_I[m] == initial_I + prod_I[m] - dI)
        else:
            model.addConstr(inv_I[m] == inv_I[months[idx-1]] + prod_I[m] - dI)

        dII = demand_II[str(m)]
        if m == months[0]:
            model.addConstr(inv_II[m] == 0 + prod_II[m] - dII)
        else:
            model.addConstr(inv_II[m] == inv_II[months[idx-1]] + prod_II[m] - dII)

        # Capacity constraint
        model.addConstr(prod_I[m] + prod_II[m] <= capacity)

        # Storage relations and capacity
        vol_I = inv_I[m] * unit_vol_I
        vol_II = inv_II[m] * unit_vol_II
        total_vol = vol_I + vol_II
        model.addConstr(own_storage[m] + external_storage[m] == total_vol)
        model.addConstr(own_storage[m] <= own_capacity)

    # Objective
    objective = gp.quicksum(prod_cost_I * prod_I[m] + prod_cost_II * prod_II[m] for m in months)
    objective += gp.quicksum(own_storage_cost * own_storage[m] + external_storage_cost * external_storage[m] for m in months)
    model.setObjective(objective, GRB.MINIMIZE)

    # Assemble variables dictionary with exact keys
    variables = {}
    for m in months:
        variables[f"prod_I_{m}"] = prod_I[m]
        variables[f"prod_II_{m}"] = prod_II[m]
        variables[f"inv_I_{m}"] = inv_I[m]
        variables[f"inv_II_{m}"] = inv_II[m]
        variables[f"own_storage_{m}"] = own_storage[m]
        variables[f"external_storage_{m}"] = external_storage[m]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }