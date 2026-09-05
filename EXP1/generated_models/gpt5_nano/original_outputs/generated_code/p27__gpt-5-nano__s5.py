import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    nodes = data["nodes"]
    start = data.get("start_node", nodes[0])
    dist = data["distance"]

    model = gp.Model("TSP_MTz")

    # Create x variables: x[i,j] = 1 if arc i->j is used
    x = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            x[(i, j)] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    # Create MTZ u variables for i in 2..n (excluding start)
    u = {}
    n = len(nodes)
    for i in nodes:
        if i == start:
            continue
        u[i] = model.addVar(vtype=GRB.CONTINUOUS, name=f"u_{i}", lb=2, ub=n)

    model.update()

    # Objective: minimize total distance
    model.setObjective(gp.quicksum(dist[f"{i},{j}"] * x[(i, j)]
                                   for i in nodes for j in nodes if i != j), GRB.MINIMIZE)

    # Outgoing degree constraints: exactly one outgoing arc from each node
    for i in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for j in nodes if j != i) == 1, name=f"out_{i}")

    # Incoming degree constraints: exactly one incoming arc to each node
    for j in nodes:
        model.addConstr(gp.quicksum(x[(i, j)] for i in nodes if i != j) == 1, name=f"in_{j}")

    # MTZ subtour elimination constraints
    for i in nodes:
        if i == start:
            continue
        for j in nodes:
            if j == start or i == j:
                continue
            model.addConstr(u[i] - u[j] + n * x[(i, j)] <= n - 1)

    model.update()

    # Build the variables dictionary to return
    variables = {}
    for (i, j), var in x.items():
        variables[f"x_{i}_{j}"] = var
    for i in nodes:
        if i == start:
            continue
        variables[f"u_{i}"] = u[i]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    objective = float(model.ObjVal)

    # Prepare solution with all required keys
    x_keys = [
        "x_1_2","x_1_3","x_1_4","x_1_5","x_1_6","x_1_7",
        "x_2_1","x_2_3","x_2_4","x_2_5","x_2_6","x_2_7",
        "x_3_1","x_3_2","x_3_4","x_3_5","x_3_6","x_3_7",
        "x_4_1","x_4_2","x_4_3","x_4_5","x_4_6","x_4_7",
        "x_5_1","x_5_2","x_5_3","x_5_4","x_5_6","x_5_7",
        "x_6_1","x_6_2","x_6_3","x_6_4","x_6_5","x_6_7",
        "x_7_1","x_7_2","x_7_3","x_7_4","x_7_5","x_7_6"
    ]
    u_keys = ["u_2","u_3","u_4","u_5","u_6","u_7"]

    solution = {}
    for k in x_keys + u_keys:
        solution[k] = float(variables[k].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }