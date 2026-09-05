import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()

    # Data extraction
    container_ids = data.get("container_ids", [])
    max_containers = int(data.get("max_containers_available", len(container_ids)))
    goods = data.get("goods", ["A","B","C","D","E"])
    quantity = data.get("quantity", {})
    weights = data.get("weight_tons", {})
    capacity = data.get("container_capacity_tons", 0.0)
    min_load = data.get("minimum_load_tons_if_used", 0.0)

    # Precompute max quantities per good
    max_qty = {g: int(quantity[g]) for g in goods}

    # Decision variables
    y = {}    # container used
    for i in range(1, max_containers + 1):
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")

    uA = {}   # indicator: container loads any A
    for i in range(1, max_containers + 1):
        uA[i] = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")

    # q_i_g: units of good g in container i
    q = {}
    for i in range(1, max_containers + 1):
        q[i] = {}
        for g in goods:
            q[i][g] = model.addVar(vtype=GRB.INTEGER, lb=0, ub=max_qty[g],
                                   name=f"q_{i}_{g}")

    # Build the objective and constraints

    # 1. Totals: for each good, the sum over containers equals total quantity
    for g in goods:
        total_eq = gp.quicksum(q[i][g] for i in range(1, max_containers + 1))
        model.addConstr(total_eq == quantity[g], name=f"total_{g}")

    # 2. Container capacity and minimum load constraints
    for i in range(1, max_containers + 1):
        total_weight_i = gp.quicksum(weights[g] * q[i][g] for g in goods)
        model.addConstr(total_weight_i <= capacity * y[i], name=f"cap_{i}")
        model.addConstr(total_weight_i >= min_load * y[i], name=f"minload_{i}")

        # 3. Linking items to container usage: if container not used, all items zero
        for g in goods:
            model.addConstr(q[i][g] <= max_qty[g] * y[i], name=f"lb_ub_{i}_{g}")

    # 4. A-C relationship:
    # A and C relate as: if A loaded then C must be loaded
    # We implement A <= maxA * qC and A >= uA and A <= maxA * uA to tie uA to A presence
    maxA = max_qty["A"]
    for i in range(1, max_containers + 1):
        # A presence indicator
        model.addConstr(q[i]["A"] >= uA[i], name=f"A_geq_uA_{i}")
        model.addConstr(q[i]["A"] <= maxA * uA[i], name=f"A_leq_maxA_uA_{i}")
        # A implies C: A <= maxA * C
        model.addConstr(q[i]["A"] <= maxA * q[i]["C"], name=f"A_leq_maxA_C_{i}")

    # 5. Objective: minimize number of used containers
    model.setObjective(gp.quicksum(y[i] for i in range(1, max_containers + 1)), GRB.MINIMIZE)

    # Return model and a flat dictionary of all required variables
    variables = {}
    for i in range(1, max_containers + 1):
        variables[f"y_{i}"] = y[i]
    for i in range(1, max_containers + 1):
        variables[f"uA_{i}"] = uA[i]
    for i in range(1, max_containers + 1):
        for g in goods:
            key = f"q_{i}_{g}"
            variables[key] = q[i][g]

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    from gurobipy import GRB
    if model.Status == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif model.Status == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif model.Status == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif model.Status == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif model.Status == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(model.Status)

    objective_value = float(model.ObjVal)

    # Build solution dictionary with all required keys and values
    solution = {}
    # y_1 ... y_10
    for i in range(1, int(data.get("max_containers_available", 10)) + 1):
        key = f"y_{i}"
        solution[key] = float(variables[key].X)

    goods = data.get("goods", ["A","B","C","D","E"])
    # uA_1 ... uA_10
    for i in range(1, int(data.get("max_containers_available", 10)) + 1):
        key = f"uA_{i}"
        solution[key] = float(variables[key].X)

    # q_i_g: q_{i}_{g}
    for i in range(1, int(data.get("max_containers_available", 10)) + 1):
        for g in goods:
            key = f"q_{i}_{g}"
            solution[key] = float(variables[key].X)

    result = {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }

    return result