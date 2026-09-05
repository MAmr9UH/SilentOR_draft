import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    """
    Build the Gurobi model for the container packing problem.
    Returns (model, variables) where variables is a dict with EXACT keys:
    y_1,...,y_10, uA_1,...,uA_10, q_i_G for i=1..10 and G in {A,B,C,D,E}
    """
    model = gp.Model()

    container_ids = data.get("container_ids", list(range(1, 11)))
    goods = data.get("goods", ["A", "B", "C", "D", "E"])
    qty = data["quantity"]
    weight = data["weight_tons"]
    capacity = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    min_D = data["minimum_D_units_if_used"]
    max_containers = data.get("max_containers_available", 10)
    A_total = qty["A"]

    # Decision variables
    y = {}
    for i in range(1, 11):
        y[i] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")

    uA = {}
    for i in range(1, 11):
        uA[i] = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")

    q = {}
    for i in range(1, 11):
        for g in goods:
            ub = int(qty[g])
            q[(i, g)] = model.addVar(vtype=GRB.INTEGER, lb=0, ub=ub, name=f"q_{i}_{g}")

    model.update()

    # Objective: minimize number of containers used
    model.setObjective(gp.quicksum(y[i] for i in range(1, 11)), GRB.MINIMIZE)

    # Constraints per container
    for i in range(1, 11):
        total_weight = gp.quicksum(weight[g] * q[(i, g)] for g in goods)

        # Capacity constraint: 0 <= total_weight <= capacity * y_i
        model.addConstr(total_weight <= capacity * y[i], name=f"cap_{i}")

        # Minimum load if container is used
        model.addConstr(total_weight >= min_load * y[i], name=f"minload_{i}")

        # D minimum if used
        model.addConstr(q[(i, "D")] >= min_D * y[i], name=f"minD_{i}")

        # A/C linkage using auxiliary uA_i
        sum_A = q[(i, "A")]
        sum_C = q[(i, "C")]

        # If any A is loaded in container i, then uA_i must be 1 (and A must be at most M * uA)
        model.addConstr(sum_A <= A_total * uA[i], name=f"A_tie_ub_{i}")
        model.addConstr(sum_A >= uA[i], name=f"A_tie_lb_{i}")

        # If any A is loaded, at least one C must be loaded in same container
        model.addConstr(sum_C >= uA[i], name=f"A_requires_C_{i}")

    # Totals per good
    for g in goods:
        model.addConstr(gp.quicksum(q[(i, g)] for i in range(1, 11)) == qty[g], name=f"tot_{g}")

    # Build and return the variables dictionary with EXACT keys
    variables = {}
    for i in range(1, 11):
        variables[f"y_{i}"] = y[i]
    for i in range(1, 11):
        variables[f"uA_{i}"] = uA[i]
    for i in range(1, 11):
        for g in goods:
            variables[f"q_{i}_{g}"] = q[(i, g)]

    return model, variables

def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the solution as a dict with the required schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary
    solution = {}

    # y variables
    for i in range(1, 11):
        solution[f"y_{i}"] = int(round(variables[f"y_{i}"].X))

    # uA variables
    for i in range(1, 11):
        solution[f"uA_{i}"] = int(round(variables[f"uA_{i}"].X))

    # q variables
    goods = data.get("goods", ["A", "B", "C", "D", "E"])
    for i in range(1, 11):
        for g in goods:
            key = f"q_{i}_{g}"
            solution[key] = int(round(variables[key].X))

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }