def build_model(data: dict) -> tuple:
    import gurobipy as gp
    from gurobipy import GRB

    nodes = list(data["nodes"])
    n = len(nodes)

    # Build distance lookup
    dist = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                key = f"{i},{j}"
                dist[(i, j)] = data["distance"][key]

    model = gp.Model()

    # Decision variables x_i_j
    x = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                x[(i, j)] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    # MTZ order variables u_i for i in 2..n
    u = {}
    for i in nodes:
        if i != 1:
            u[i] = model.addVar(vtype=GRB.INTEGER, lb=2, ub=n, name=f"u_{i}")

    model.update()

    # Objective: minimize total distance
    model.setObjective(gp.quicksum(dist[(i, j)] * x[(i, j)] for i in nodes for j in nodes if i != j), GRB.MINIMIZE)

    # Flow constraints: each node has exactly one outgoing arc and exactly one incoming arc
    for i in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for j in nodes if j != i) == 1, name=f"out_{i}")
    for j in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for i in nodes if i != j) == 1, name=f"in_{j}")

    # MTZ subtour elimination constraints
    m = n
    for i in nodes:
        if i == 1:
            continue
        for j in nodes:
            if j == 1 or i == j:
                continue
            model.addConstr(u[i] - u[j] + m * x[(i, j)] <= m - 1)

    model.update()

    # Collect variables into a flat dict with exact keys
    variables = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                variables[f"x_{i}_{j}"] = x[(i, j)]
    for i in nodes:
        if i != 1:
            variables[f"u_{i}"] = u[i]

    return model, variables

def solve(data: dict) -> dict:
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for key in variables:
        solution[key] = variables[key].X

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }