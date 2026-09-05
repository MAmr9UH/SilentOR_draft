import gurobipy as gp

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi model for the container packing problem.
    Returns: (model, variables)
      - variables is a dict with exact keys as specified and corresponding Var objects.
    """
    model = gp.Model()

    # Read data
    container_ids = data["container_ids"]  # e.g., [1,2,...,10]
    goods = data["goods"]  # ["A","B","C","D","E"]
    quantity = data["quantity"]  # dict: {'A':120, ...}
    weight_tons = data["weight_tons"]  # dict: {'A':0.5, ...}
    cap = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    min_D_units = data["minimum_D_units_if_used"]

    max_A_units = quantity["A"]  # 120

    # Decision variables
    y = {}   # 1 if container i is used
    uA = {}  # 1 if container i loads any A goods
    q = {}   # units of each good in each container

    for i in container_ids:
        y[i] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{i}")
        uA[i] = model.addVar(vtype=gp.GRB.BINARY, name=f"uA_{i}")

    for i in container_ids:
        for g in goods:
            q[(i, g)] = model.addVar(vtype=gp.GRB.INTEGER, lb=0, name=f"q_{i}_{g}")

    model.update()

    # Capacity constraints and loading constraints per container
    M_A = max_A_units  # Big-M constant for A/C linkage

    for i in container_ids:
        total_weight = gp.quicksum(weight_tons[g] * q[(i, g)] for g in goods)

        # Capacity: each used container must have total weight <= 60, and if not used it's 0
        model.addConstr(total_weight <= cap * y[i])

        # Minimum load when used: total weight >= 18 * y_i
        model.addConstr(total_weight >= min_load * y[i])

        # Minimum D units when used
        model.addConstr(weight_tons["D"] * q[(i, "D")] >= min_D_units * y[i])

        # A -> C: q_i_A <= M * q_i_C
        model.addConstr(q[(i, "A")] <= M_A * q[(i, "C")])

        # Link A presence to uA_i
        model.addConstr(q[(i, "A")] >= uA[i])
        model.addConstr(q[(i, "A")] <= M_A * uA[i])

    # Global demand satisfaction: total across all containers equals quantity
    for g in goods:
        model.addConstr(gp.quicksum(q[(i, g)] for i in container_ids) == quantity[g])

    # Objective: minimize number of used containers
    model.setObjective(gp.quicksum(y[i] for i in container_ids), gp.GRB.MINIMIZE)

    # Prepare variables dict with exact keys
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
    """
    Build the model, solve it, and return the solution in the specified JSON-like schema.
    Returns:
      {
        "type": "object",
        "status": "<status_string>",
        "objective": <float>,
        "solution": {
          "y_1": int, ..., "q_10_E": int, ...
        }
      }
    """
    # Silence solver output for compatibility
    model, variables = build_model(data)
    try:
        model.Params.OutputFlag = 0
    except Exception:
        try:
            model.setParam("OutputFlag", 0)
        except Exception:
            pass

    model.optimize()

    # Map status to string
    status_lookup = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    st = model.Status
    status_str = status_lookup.get(st, str(st))

    model.update()
    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dict with values for all required keys
    solution = {}
    for i in data["container_ids"]:
        solution[f"y_{i}"] = int(variables[f"y_{i}"].X)
    for i in data["container_ids"]:
        solution[f"uA_{i}"] = int(variables[f"uA_{i}"].X)
    for i in data["container_ids"]:
        for g in data["goods"]:
            solution[f"q_{i}_{g}"] = int(variables[f"q_{i}_{g}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }