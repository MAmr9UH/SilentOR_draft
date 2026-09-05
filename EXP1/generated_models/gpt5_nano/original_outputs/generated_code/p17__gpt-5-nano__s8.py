import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model("LogistiCorp")
    model.setParam('OutputFlag', 0)

    centers = data["centers"]
    stores = data["stores"]

    # Decision variables
    y = {}
    for idx in range(1, len(centers) + 1):
        key = f"y_c{idx}"
        y[key] = model.addVar(vtype=GRB.BINARY, name=key)

    f = {}
    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            key = f"f_c{i}_s{j}"
            f[key] = model.addVar(vtype=GRB.CONTINUOUS, name=key)

    model.update()

    # Objective: opening costs + transportation costs
    opening_costs = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]

    obj = gp.quicksum(opening_costs[f"c{idx}"] * y[f"y_c{idx}"] for idx in range(1, len(centers) + 1))

    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            cst = transport_cost[f"c{i}"][f"s{j}"]
            obj += cst * f[f"f_c{i}_s{j}"]

    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Demand constraints: sum_i f_i_j = demand_j
    for j_idx, s in enumerate(stores, start=1):
        demand = data["demand"][f"s{j_idx}"]
        model.addConstr(gp.quicksum(f[f"f_c{i}_s{j_idx}"] for i in range(1, len(centers) + 1)) == demand,
                        name=f"demand_{s}")

    # Capacity constraints: sum_j f_i_j <= capacity_i * y_i
    for i_idx, c in enumerate(centers, start=1):
        cap = data["capacity"][f"c{i_idx}"]
        model.addConstr(gp.quicksum(f[f"f_c{i_idx}_s{j}"] for j in range(1, len(stores) + 1)) <= cap * y[f"y_c{i_idx}"],
                        name=f"cap_{c}")

    model.update()

    # Build variables dict to return
    variables = {}
    for idx in range(1, len(centers) + 1):
        variables[f"y_c{idx}"] = y[f"y_c{idx}"]
    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            variables[f"f_c{i}_s{j}"] = f[f"f_c{i}_s{j}"]

    return model, variables

def solve(data: dict):
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_int)

    objective_value = float(model.ObjVal)

    solution = {}
    centers = data["centers"]
    stores = data["stores"]

    for idx in range(1, len(centers) + 1):
        solution[f"y_c{idx}"] = float(variables[f"y_c{idx}"].X)

    for i in range(1, len(centers) + 1):
        for j in range(1, len(stores) + 1):
            solution[f"f_c{i}_s{j}"] = float(variables[f"f_c{i}_s{j}"].X)

    return {
        "status": status,
        "objective": objective_value,
        "solution": solution
    }