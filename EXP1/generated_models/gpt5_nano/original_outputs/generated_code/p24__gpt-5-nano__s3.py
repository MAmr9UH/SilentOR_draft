import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    container_ids = data["container_ids"]
    goods = data["goods"]
    quantity = data["quantity"]
    weights = data["weight_tons"]
    cap = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    max_A_per_container = int(cap / weights["A"]) if weights["A"] > 0 else 0

    # Decision variables
    variables = {}

    # y_i: container i is used
    for i in container_ids:
        key = f"y_{i}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # uA_i: container i loads any A goods
    for i in container_ids:
        key = f"uA_{i}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # q_{i}_{g}: units of good g loaded in container i
    for i in container_ids:
        for g in goods:
            key = f"q_{i}_{g}"
            v = model.addVar(vtype=GRB.INTEGER, lb=0, name=key)
            variables[key] = v

    # Objective: minimize number of used containers
    model.setObjective(quicksum(variables[f"y_{i}"] for i in container_ids), GRB.MINIMIZE)

    # Supply constraints: total quantity of each good packed across containers equals demand
    for g in goods:
        model.addConstr(
            quicksum(variables[f"q_{i}_{g}"] for i in container_ids) == quantity[g],
            name=f"Supply_{g}"
        )

    # Capacity and minimum load per used container
    for i in container_ids:
        total_weight = quicksum(weights[g] * variables[f"q_{i}_{g}"] for g in goods)
        model.addConstr(total_weight <= cap * variables[f"y_{i}"], name=f"Cap_{i}")
        model.addConstr(total_weight >= min_load * variables[f"y_{i}"], name=f"MinLoad_{i}")

        # A requires at least one C in the same container
        model.addConstr(variables[f"q_{i}_A"] <= max_A_per_container * variables[f"uA_{i}"], name=f"Amax_{i}")
        model.addConstr(variables[f"q_{i}_A"] >= variables[f"uA_{i}"], name=f"A_presence_min_{i}")
        model.addConstr(variables[f"q_{i}_C"] >= variables[f"uA_{i}"], name=f"C_presence_from_A_{i}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    status = model.Status

    if status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    obj_val = float(model.ObjVal)

    # Build solution dictionary
    solution = {}
    container_ids = data["container_ids"]
    goods = data["goods"]

    for i in container_ids:
        solution[f"y_{i}"] = float(variables[f"y_{i}"].X)
        solution[f"uA_{i}"] = float(variables[f"uA_{i}"].X)

    for i in container_ids:
        for g in goods:
            solution[f"q_{i}_{g}"] = int(variables[f"q_{i}_{g}"].X)

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }