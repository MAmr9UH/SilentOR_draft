import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    nodes = data.get("nodes", [])
    N = len(nodes)
    start_node = data.get("start_node", nodes[0] if nodes else 1)

    # Build distance lookup
    dist = {}
    distance_dict = data.get("distance", {})
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"{i},{j}"
            if key in distance_dict:
                dist[(i, j)] = distance_dict[key]
            else:
                raise KeyError(f"Distance missing for edge {i}->{j}")

    model = gp.Model()

    # Variables: x_i_j for all i != j
    variables = {}

    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            var_name = f"x_{i}_{j}"
            v = model.addVar(vtype=GRB.BINARY, name=var_name)
            variables[var_name] = v

    # MTZ order variables u_2 .. u_7
    for i in range(2, N + 1):
        key = f"u_{i}"
        v = model.addVar(vtype=GRB.INTEGER, lb=2, ub=N, name=key)
        variables[key] = v

    model.update()

    # Outgoing constraints: each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(
            quicksum(variables[f"x_{i}_{j}"] for j in nodes if j != i) == 1,
            name=f"out_{i}"
        )

    # Incoming constraints: each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(
            quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1,
            name=f"in_{j}"
        )

    # MTZ subtour elimination constraints
    # For i,j in {2,...,N}, i != j
    for i in range(2, N + 1):
        for j in range(2, N + 1):
            if i == j:
                continue
            model.addConstr(
                variables[f"u_{i}"] - variables[f"u_{j}"] + N * variables[f"x_{i}_{j}"] <= N - 1,
                name=f"mtz_{i}_{j}"
            )

    # Objective: minimize total distance
    model.setObjective(
        quicksum(dist[(i, j)] * variables[f"x_{i}_{j}"] for i in nodes for j in nodes if i != j),
        GRB.MINIMIZE
    )

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Ensure we can read values
    model.update()
    status = model.Status
    status_str = "UNKNOWN"
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

    obj_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with required keys
    solution = {}

    # x variables
    for i in data.get("nodes", []):
        for j in data.get("nodes", []):
            if i == j:
                continue
            key = f"x_{i}_{j}"
            if key in variables:
                solution[key] = float(variables[key].X)

    # u variables
    for i in range(2, len(data.get("nodes", [])) + 1):
        key = f"u_{i}"
        if key in variables:
            solution[key] = float(variables[key].X)

    result = {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }

    return result