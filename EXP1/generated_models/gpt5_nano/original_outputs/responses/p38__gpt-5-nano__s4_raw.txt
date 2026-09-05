import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    months = data["months"]
    demand_I_map = data["demand"]["I"]
    demand_II_map = data["demand"]["II"]

    def get_demand(dmap, m):
        # supports int or str keys
        if isinstance(m, int):
            if m in dmap:
                return dmap[m]
            if str(m) in dmap:
                return dmap[str(m)]
        else:
            if m in dmap:
                return dmap[m]
            if str(m) in dmap:
                return dmap[str(m)]
        return 0

    cost_I = data["production_cost"]["I"]
    cost_II = data["production_cost"]["II"]

    max_capacity = data["monthly_total_production_capacity"]

    vol_I = data["unit_volume"]["I"]
    vol_II = data["unit_volume"]["II"]

    own_cap = data["own_warehouse_capacity_cubic_m"]
    own_cost = data["own_storage_cost_per_cubic_m_month"]
    ext_cost = data["external_storage_cost_per_cubic_m_month"]

    variables = {}

    prod_I_vars = {}
    prod_II_vars = {}
    inv_I_vars = {}
    inv_II_vars = {}
    own_storage_vars = {}
    external_storage_vars = {}

    for m in months:
        v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_I_{m}")
        prod_I_vars[m] = v
        variables[f"prod_I_{m}"] = v

        w = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"prod_II_{m}")
        prod_II_vars[m] = w
        variables[f"prod_II_{m}"] = w

        iv = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_I_{m}")
        inv_I_vars[m] = iv
        variables[f"inv_I_{m}"] = iv

        iv2 = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"inv_II_{m}")
        inv_II_vars[m] = iv2
        variables[f"inv_II_{m}"] = iv2

        os = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"own_storage_{m}")
        own_storage_vars[m] = os
        variables[f"own_storage_{m}"] = os

        es = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"external_storage_{m}")
        external_storage_vars[m] = es
        variables[f"external_storage_{m}"] = es

    model.update()

    # Demand constraints and inventory balance
    for idx, m in enumerate(months):
        dI = get_demand(demand_I_map, m)
        dII = get_demand(demand_II_map, m)

        if idx == 0:
            model.addConstr(inv_I_vars[m] == prod_I_vars[m] - dI)
            model.addConstr(inv_II_vars[m] == prod_II_vars[m] - dII)
        else:
            prev = months[idx - 1]
            model.addConstr(inv_I_vars[m] == inv_I_vars[prev] + prod_I_vars[m] - dI)
            model.addConstr(inv_II_vars[m] == inv_II_vars[prev] + prod_II_vars[m] - dII)

        # capacity
        model.addConstr(prod_I_vars[m] + prod_II_vars[m] <= max_capacity)

        # storage balance by volumes
        model.addConstr(vol_I * inv_I_vars[m] + vol_II * inv_II_vars[m] == own_storage_vars[m] + external_storage_vars[m])

        # own storage capacity
        model.addConstr(own_storage_vars[m] <= own_cap)

    # Objective
    objective = gp.quicksum(prod_I_vars[m] * cost_I for m in months) \
                + gp.quicksum(prod_II_vars[m] * cost_II for m in months) \
                + gp.quicksum(own_storage_vars[m] * own_cost for m in months) \
                + gp.quicksum(external_storage_vars[m] * ext_cost for m in months)

    model.setObjective(objective, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))
    objective = float(model.ObjVal)

    solution = {}
    for m in data["months"]:
        solution[f"prod_I_{m}"] = float(variables[f"prod_I_{m}"].X)
        solution[f"prod_II_{m}"] = float(variables[f"prod_II_{m}"].X)
    for m in data["months"]:
        solution[f"inv_I_{m}"] = float(variables[f"inv_I_{m}"].X)
        solution[f"inv_II_{m}"] = float(variables[f"inv_II_{m}"].X)
    for m in data["months"]:
        solution[f"own_storage_{m}"] = float(variables[f"own_storage_{m}"].X)
        solution[f"external_storage_{m}"] = float(variables[f"external_storage_{m}"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }