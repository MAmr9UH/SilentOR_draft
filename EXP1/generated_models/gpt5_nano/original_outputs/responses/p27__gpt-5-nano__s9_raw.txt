import gurobipy as gp

def build_model(data: dict) -> tuple:
    nodes = data.get("nodes", [])
    n = len(nodes)
    distance = data.get("distance", {})
    # Build distance map for quick lookup
    dist = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"{i},{j}"
            dist[(i, j)] = distance[key]

    model = gp.Model()

    # Decision variables x_i_j for all i != j
    variables = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    # MTZ order variables u_i for i in {2,...,n}
    for i in nodes:
        if i == 1:
            continue
        key = f"u_{i}"
        variables[key] = model.addVar(vtype=gp.GRB.INTEGER, lb=2, ub=n, name=key)

    model.update()

    # Objective: minimize total distance
    model.setObjective(gp.quicksum(dist[(i, j)] * variables[f"x_{i}_{j}"]
                                   for i in nodes for j in nodes if i != j),
                       gp.GRB.MINIMIZE)

    # Outgoing degree constraints: each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(gp.quicksum(variables[f"x_{i}_{j}"] for j in nodes if j != i) == 1)

    # Incoming degree constraints: each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(gp.quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1)

    # MTZ subtour elimination constraints
    for i in nodes:
        if i == 1:
            continue
        for j in nodes:
            if j == 1 or i == j:
                continue
            model.addConstr(variables[f"u_{i}"] - variables[f"u_{j}"] + n * variables[f"x_{i}_{j}"] <= n - 1)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to human-readable string
    status_code = model.Status
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
        gp.GRB.SUBOPTIMAL: "SUBOPTIMAL",
        gp.GRB.INTERRUPTED: "INTERRUPTED",
        gp.GRB.SOLVED: "SOLVED",
        gp.GRB.NO_SOLUTION: "NO_SOLUTION"
    }
    status = status_map.get(status_code, str(status_code))

    obj_val = float(model.ObjVal) if model.SolCount > 0 else None

    # Build solution dictionary in required order
    solution = {}
    order_x = [
        "x_1_2","x_1_3","x_1_4","x_1_5","x_1_6","x_1_7",
        "x_2_1","x_2_3","x_2_4","x_2_5","x_2_6","x_2_7",
        "x_3_1","x_3_2","x_3_4","x_3_5","x_3_6","x_3_7",
        "x_4_1","x_4_2","x_4_3","x_4_5","x_4_6","x_4_7",
        "x_5_1","x_5_2","x_5_3","x_5_4","x_5_6","x_5_7",
        "x_6_1","x_6_2","x_6_3","x_6_4","x_6_5","x_6_7",
        "x_7_1","x_7_2","x_7_3","x_7_4","x_7_5","x_7_6"
    ]
    for k in order_x:
        solution[k] = float(variables[k].X)

    for i in [2,3,4,5,6,7]:
        solution[f"u_{i}"] = float(variables[f"u_{i}"].X)

    return {
        "type": "object",
        "status": status,
        "objective": obj_val,
        "solution": solution
    }