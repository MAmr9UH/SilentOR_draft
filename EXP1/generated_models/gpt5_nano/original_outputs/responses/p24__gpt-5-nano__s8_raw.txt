import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    container_ids = data["container_ids"]
    goods = data["goods"]
    weight_tons = data["weight_tons"]

    capacity = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    min_D_units = data["minimum_D_units_if_used"]
    A_total = data["quantity"]["A"]

    # Decision variables
    y = {}
    for i in container_ids:
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")

    uA = {}
    for i in container_ids:
        uA[i] = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")

    q = {}
    for i in container_ids:
        for g in goods:
            q[(i, g)] = model.addVar(vtype=GRB.INTEGER, name=f"q_{i}_{g}")

    model.update()

    # Objective: minimize number of used containers
    model.setObjective(gp.quicksum(y[i] for i in container_ids), GRB.MINIMIZE)

    # Demand constraints: exactly allocate all quantities
    for g in goods:
        model.addConstr(gp.quicksum(q[(i, g)] for i in container_ids) == data["quantity"][g])

    # Capacity and minimum load per container
    for i in container_ids:
        total_weight = gp.quicksum(weight_tons[g] * q[(i, g)] for g in goods)
        model.addConstr(total_weight <= capacity * y[i])
        model.addConstr(total_weight >= min_load * y[i])
        # Minimum D per used container
        model.addConstr(q[(i, "D")] >= min_D_units * y[i])

    # A/C dependency: if A is loaded then at least one C in same container
    for i in container_ids:
        model.addConstr(q[(i, "A")] <= A_total * uA[i])
        model.addConstr(q[(i, "A")] >= uA[i])
        model.addConstr(q[(i, "C")] >= uA[i])

    # Ensure the A/C relationship is respected via variables
    # The A must be accompanied by at least one C if A is present in the container
    # (Handled by the above sum_C >= uA and q_A >= uA with q_A <= A_total*uA)

    # Prepare variables dictionary to return
    variables = {}
    for i in container_ids:
        variables[f"y_{i}"] = y[i]
    for i in container_ids:
        variables[f"uA_{i}"] = uA[i]
    for i in container_ids:
        for g in goods:
            variables[f"q_{i}_{g}"] = q[(i, g)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = model.Status
    status_str = status_map.get(status, str(status))

    objective = float(model.ObjVal)

    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }