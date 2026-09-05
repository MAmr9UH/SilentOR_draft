import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    months = data["months"]  # [7,6? actually 7-12], but per input it's 7..12
    cap = data["monthly_total_production_capacity"]
    own_cap = data["own_warehouse_capacity_cubic_m"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]
    unit_I = data["unit_volume"]["I"]
    unit_II = data["unit_volume"]["II"]

    demand_I = {m: data["demand"]["I"][str(m)] for m in months}
    demand_II = {m: data["demand"]["II"][str(m)] for m in months}
    cost_I = data["production_cost"]["I"]
    cost_II = data["production_cost"]["II"]

    prodI = {}
    prodII = {}
    invI = {}
    invII = {}
    own = {}
    ext = {}

    # Create variables
    for m in months:
        prodI[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_I_{m}")
        prodII[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_II_{m}")
        invI[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_I_{m}")
        invII[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_II_{m}")
        own[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"own_storage_{m}")
        ext[m] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"external_storage_{m}")

    model.update()

    # Constraints
    for idx, m in enumerate(months):
        if idx == 0:
            # July, initial inventory is zero
            model.addConstr(invI[m] == prodI[m] - demand_I[m], name=f"bal_I_{m}")
            model.addConstr(invII[m] == prodII[m] - demand_II[m], name=f"bal_II_{m}")
        else:
            prev = months[idx - 1]
            model.addConstr(invI[m] == invI[prev] + prodI[m] - demand_I[m], name=f"bal_I_{m}")
            model.addConstr(invII[m] == invII[prev] + prodII[m] - demand_II[m], name=f"bal_II_{m}")

        # Nonnegativity of inventory (redundant if lb=0, but explicit)
        model.addConstr(invI[m] >= 0, name=f"invI_nonneg_{m}")
        model.addConstr(invII[m] >= 0, name=f"invII_nonneg_{m}")

        # Capacity
        model.addConstr(prodI[m] + prodII[m] <= cap, name=f"cap_{m}")

        # Storage balance: end-of-month storage must fit in own + external
        vol_end = unit_I * invI[m] + unit_II * invII[m]
        model.addConstr(own[m] + ext[m] == vol_end, name=f"storage_cont_{m}")
        model.addConstr(own[m] <= own_cap, name=f"own_cap_{m}")

    # Objective: production cost + storage cost
    prod_cost = gp.quicksum(prodI[m] * cost_I for m in months) + gp.quicksum(prodII[m] * cost_II for m in months)
    storage_cost = gp.quicksum(own[m] * own_cost for m in months) + gp.quicksum(ext[m] * ext_cost for m in months)
    model.setObjective(prod_cost + storage_cost)

    # Build variables dict with exact keys
    variables = {}
    for m in months:
        variables[f"prod_I_{m}"] = prodI[m]
        variables[f"prod_II_{m}"] = prodII[m]
        variables[f"inv_I_{m}"] = invI[m]
        variables[f"inv_II_{m}"] = invII[m]
        variables[f"own_storage_{m}"] = own[m]
        variables[f"external_storage_{m}"] = ext[m]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    # Build solution dictionary
    solution = {}
    for key in sorted(variables.keys()):
        solution[key] = float(variables[key].X)

    objective_value = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }