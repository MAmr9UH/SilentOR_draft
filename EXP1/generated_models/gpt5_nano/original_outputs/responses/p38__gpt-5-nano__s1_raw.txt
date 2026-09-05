import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    months = data["months"]
    initial_inv_I = data["initial_inventory"]["I"]
    initial_inv_II = data["initial_inventory"]["II"]

    demand_I = data["demand"]["I"]
    demand_II = data["demand"]["II"]

    cap = data["monthly_total_production_capacity"]
    vol_I = data["unit_volume"]["I"]
    vol_II = data["unit_volume"]["II"]

    own_cap = data["own_warehouse_capacity_cubic_m"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    prod_I = {}
    prod_II = {}
    inv_I = {}
    inv_II = {}
    own_storage = {}
    external_storage = {}

    # Create variables for each month
    for j in months:
        key_pI = f"prod_I_{j}"
        key_pII = f"prod_II_{j}"
        key_iI = f"inv_I_{j}"
        key_iII = f"inv_II_{j}"
        key_o = f"own_storage_{j}"
        key_e = f"external_storage_{j}"

        prod_I[key_pI] = m.addVar(lb=0.0, name=key_pI)
        prod_II[key_pII] = m.addVar(lb=0.0, name=key_pII)
        inv_I[key_iI] = m.addVar(lb=0.0, name=key_iI)
        inv_II[key_iII] = m.addVar(lb=0.0, name=key_iII)
        own_storage[key_o] = m.addVar(lb=0.0, name=key_o)
        external_storage[key_e] = m.addVar(lb=0.0, name=key_e)

    m.update()

    # Inventory balance constraints
    for idx, j in enumerate(months):
        if idx == 0:
            m.addConstr(inv_I[f"inv_I_{j}"] == initial_inv_I + prod_I[f"prod_I_{j}"] - demand_I[str(j)])
            m.addConstr(inv_II[f"inv_II_{j}"] == initial_inv_II + prod_II[f"prod_II_{j}"] - demand_II[str(j)])
        else:
            prev = months[idx - 1]
            m.addConstr(inv_I[f"inv_I_{j}"] == inv_I[f"inv_I_{prev}"] + prod_I[f"prod_I_{j}"] - demand_I[str(j)])
            m.addConstr(inv_II[f"inv_II_{j}"] == inv_II[f"inv_II_{prev}"] + prod_II[f"prod_II_{j}"] - demand_II[str(j)])

    # Production capacity per month
    for j in months:
        m.addConstr(prod_I[f"prod_I_{j}"] + prod_II[f"prod_II_{j}"] <= cap)

    # Storage balance: total inventory cubic meters must be stored in own + external
    for j in months:
        total_inventory_volume = vol_I * inv_I[f"inv_I_{j}"] + vol_II * inv_II[f"inv_II_{j}"]
        m.addConstr(own_storage[f"own_storage_{j}"] + external_storage[f"external_storage_{j}"] == total_inventory_volume)

        # Own storage capacity constraint
        m.addConstr(own_storage[f"own_storage_{j}"] <= own_cap)

    # Objective: minimize production + storage costs
    objective = gp.quicksum(
        data["production_cost"]["I"] * prod_I[f"prod_I_{j}"]
        + data["production_cost"]["II"] * prod_II[f"prod_II_{j}"]
        + own_storage[f"own_storage_{j}"] * own_cost
        + external_storage[f"external_storage_{j}"] * ext_cost
        for j in months
    )
    m.setObjective(objective, GRB.MINIMIZE)

    variables = {}
    for j in months:
        variables[f"prod_I_{j}"] = prod_I[f"prod_I_{j}"]
        variables[f"prod_II_{j}"] = prod_II[f"prod_II_{j}"]
        variables[f"inv_I_{j}"] = inv_I[f"inv_I_{j}"]
        variables[f"inv_II_{j}"] = inv_II[f"inv_II_{j}"]
        variables[f"own_storage_{j}"] = own_storage[f"own_storage_{j}"]
        variables[f"external_storage_{j}"] = external_storage[f"external_storage_{j}"]

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.update()
    model.optimize()

    grb = gp.GRB
    st = model.Status
    if st == grb.OPTIMAL:
        status = "OPTIMAL"
    elif st == grb.INFEASIBLE:
        status = "INFEASIBLE"
    elif st == grb.UNBOUNDED:
        status = "UNBOUNDED"
    elif st == grb.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif st == grb.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif st == grb.SUBOPTIMAL:
        status = "SUBOPTIMAL"
    elif st == grb.INTERRUPTED:
        status = "INTERRUPTED"
    else:
        status = "OTHER"

    objective_value = float(model.ObjVal)

    solution = {}
    for j in data["months"]:
        solution[f"prod_I_{j}"] = float(variables[f"prod_I_{j}"].X)
        solution[f"prod_II_{j}"] = float(variables[f"prod_II_{j}"].X)
        solution[f"inv_I_{j}"] = float(variables[f"inv_I_{j}"].X)
        solution[f"inv_II_{j}"] = float(variables[f"inv_II_{j}"].X)
        solution[f"own_storage_{j}"] = float(variables[f"own_storage_{j}"].X)
        solution[f"external_storage_{j}"] = float(variables[f"external_storage_{j}"].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective_value,
        "solution": solution
    }