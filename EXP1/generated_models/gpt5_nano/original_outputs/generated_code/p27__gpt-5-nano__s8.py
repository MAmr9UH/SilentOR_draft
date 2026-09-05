import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    nodes = data.get("nodes", [])
    n = len(nodes)
    distance = data.get("distance", {})

    # Variables
    x = {}  # (i,j) -> Var
    variables = {}

    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            var = model.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
            x[(i, j)] = var
            variables[f"x_{i}_{j}"] = var

    # MTZ order variables for non-depot nodes (2..7)
    u = {}
    for i in range(2, n + 1):
        ui = model.addVar(vtype=gp.GRB.INTEGER, name=f"u_{i}", lb=2, ub=n)
        u[i] = ui
        variables[f"u_{i}"] = ui

    model.update()

    # Constraints
    # 1) Each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for j in nodes if j != i) == 1)

    # 2) Each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for i in nodes if i != j) == 1)

    # 3) MTZ subtour elimination for non-depot nodes (i,j in 2..n)
    for i in range(2, n + 1):
        for j in range(2, n + 1):
            if i != j:
                model.addConstr(u[i] - u[j] + n * x[(i, j)] <= n - 1)

    # Objective: minimize total distance
    obj = gp.quicksum(distance[f"{i},{j}"] * x[(i, j)] for i in nodes for j in nodes if i != j)
    model.setObjective(obj, gp.GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status mapping
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dict with required keys
    solution_keys = [
        "x_1_2","x_1_3","x_1_4","x_1_5","x_1_6","x_1_7",
        "x_2_1","x_2_3","x_2_4","x_2_5","x_2_6","x_2_7",
        "x_3_1","x_3_2","x_3_4","x_3_5","x_3_6","x_3_7",
        "x_4_1","x_4_2","x_4_3","x_4_5","x_4_6","x_4_7",
        "x_5_1","x_5_2","x_5_3","x_5_4","x_5_6","x_5_7",
        "x_6_1","x_6_2","x_6_3","x_6_4","x_6_5","x_6_7",
        "x_7_1","x_7_2","x_7_3","x_7_4","x_7_5","x_7_6",
        "u_2","u_3","u_4","u_5","u_6","u_7"
    ]
    solution = {}
    for key in solution_keys:
        if key.startswith("x_"):
            solution[key] = float(variables[key].X)
        else:
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }