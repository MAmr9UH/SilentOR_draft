import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("Jul-Dec_Production_Planning")

    months = data["months"]
    variables = {}

    # Decision variables
    for t in months:
        prod_I = f"prod_I_{t}"
        prod_II = f"prod_II_{t}"
        inv_I = f"inv_I_{t}"
        inv_II = f"inv_II_{t}"
        own_store = f"own_storage_{t}"
        ext_store = f"external_storage_{t}"

        variables[prod_I] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=prod_I)
        variables[prod_II] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=prod_II)
        variables[inv_I] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=inv_I)
        variables[inv_II] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=inv_II)
        variables[own_store] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=own_store)
        variables[ext_store] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=ext_store)

    model.update()

    # Demand balance constraints
    # For Product I
    prev_inv_I = 0
    for t in months:
        prodI = variables[f"prod_I_{t}"]
        invI = variables[f"inv_I_{t}"]
        demandI = data["demand"]["I"][str(t)]
        model.addConstr(prodI + prev_inv_I == demandI + invI)
        prev_inv_I = invI

    # For Product II
    prev_inv_II = 0
    for t in months:
        prodII = variables[f"prod_II_{t}"]
        invII = variables[f"inv_II_{t}"]
        demandII = data["demand"]["II"][str(t)]
        model.addConstr(prodII + prev_inv_II == demandII + invII)
        prev_inv_II = invII

    # Storage-volume balance: total end-of-month inventory volume equals sum of storage volumes
    vol_I = data["unit_volume"]["I"]
    vol_II = data["unit_volume"]["II"]
    for t in months:
        invI = variables[f"inv_I_{t}"]
        invII = variables[f"inv_II_{t}"]
        own = variables[f"own_storage_{t}"]
        ext = variables[f"external_storage_{t}"]
        model.addConstr(vol_I * invI + vol_II * invII == own + ext)

    # Own storage capacity per month
    own_cap = data["own_warehouse_capacity_cubic_m"]
    for t in months:
        own = variables[f"own_storage_{t}"]
        model.addConstr(own <= own_cap)

    # Production capacity per month
    cap = data["monthly_total_production_capacity"]
    for t in months:
        model.addConstr(variables[f"prod_I_{t}"] + variables[f"prod_II_{t}"] <= cap)

    # Objective: minimize production costs plus storage costs
    prod_cost_I = data["production_cost"]["I"]
    prod_cost_II = data["production_cost"]["II"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    obj = gp.LinExpr()
    for t in months:
        obj += prod_cost_I * variables[f"prod_I_{t}"]
        obj += prod_cost_II * variables[f"prod_II_{t}"]
        obj += own_cost * variables[f"own_storage_{t}"]
        obj += ext_cost * variables[f"external_storage_{t}"]

    model.setObjective(obj, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    else:
        status_str = str(status_code)

    solution = {}
    for t in data["months"]:
        solution[f"prod_I_{t}"] = float(variables[f"prod_I_{t}"].X)
        solution[f"prod_II_{t}"] = float(variables[f"prod_II_{t}"].X)
        solution[f"inv_I_{t}"] = float(variables[f"inv_I_{t}"].X)
        solution[f"inv_II_{t}"] = float(variables[f"inv_II_{t}"].X)
        solution[f"own_storage_{t}"] = float(variables[f"own_storage_{t}"].X)
        solution[f"external_storage_{t}"] = float(variables[f"external_storage_{t}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }