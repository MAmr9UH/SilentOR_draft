import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Create model
    model = gp.Model()
    nodes = list(data["nodes"])
    start_node = data["start_node"]
    n = len(nodes)

    # Build distance map from data
    dist = {}
    for key, val in data["distance"].items():
        i_str, j_str = key.split(",")
        i = int(i_str); j = int(j_str)
        dist[(i, j)] = val

    # Create decision variables x_i_j for all i != j
    variables = {}
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            var_name = f"x_{i}_{j}"
            v = model.addVar(vtype=GRB.BINARY, name=var_name)
            variables[var_name] = v

    # Create MTZ order variables for non-depot nodes (2..n)
    for k in nodes:
        if k == start_node:
            continue
        var_name = f"u_{k}"
        v = model.addVar(vtype=GRB.INTEGER, lb=2, ub=n, name=var_name)
        variables[var_name] = v

    model.update()

    # Objective: minimize total distance
    model.setObjective(
        gp.quicksum(dist[(i, j)] * variables[f"x_{i}_{j}"]
                    for i in nodes for j in nodes if i != j),
        GRB.MINIMIZE
    )

    # Outgoing degree constraints: each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(
            gp.quicksum(variables[f"x_{i}_{j}"] for j in nodes if j != i) == 1,
            name=f"out_{i}"
        )

    # Incoming degree constraints: each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(
            gp.quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1,
            name=f"in_{j}"
        )

    # MTZ subtour elimination constraints
    for i in nodes:
        if i == start_node:
            continue
        for j in nodes:
            if j == start_node or i == j:
                continue
            model.addConstr(
                variables[f"u_{i}"] - variables[f"u_{j}"] + n * variables[f"x_{i}_{j}"] <= n - 1,
                name=f"mtz_{i}_{j}"
            )

    # Return model and the dictionary of variables
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    # Map status to string per problem statement
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

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with all required keys
    solution = {}

    # x variables
    for i in data["nodes"]:
        for j in data["nodes"]:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            # It's possible some vars are not created for inconsistent data; guard anyway
            if key in variables:
                solution[key] = float(variables[key].X)

    # u variables (MTZ)
    start_node = data["start_node"]
    for k in data["nodes"]:
        if k == start_node:
            continue
        key = f"u_{k}"
        if key in variables:
            solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }