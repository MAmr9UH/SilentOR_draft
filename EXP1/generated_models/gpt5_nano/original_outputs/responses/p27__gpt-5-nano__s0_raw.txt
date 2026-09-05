import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    nodes = data.get("nodes", [])
    if not nodes:
        nodes = [1, 2, 3, 4, 5, 6, 7]
    N = max(nodes)
    dist = data.get("distance", {})

    model = gp.Model("TSP_MTZ")

    # Decision variables: x_i_j for all i != j
    x = {}
    for i in nodes:
        for j in nodes:
            if i != j:
                key = f"x_{i}_{j}"
                x[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # MTZ order variables for non-depot nodes (2..N)
    u = {}
    for i in range(2, N + 1):
        key = f"u_{i}"
        u[key] = model.addVar(vtype=GRB.INTEGER, lb=2, ub=N, name=key)

    # Collect variables in a flat dictionary as required
    variables = {}
    variables.update(x)
    variables.update(u)

    # Objective: minimize total distance
    obj = gp.quicksum(dist.get(f"{i},{j}", 0) * x[f"x_{i}_{j}"] for i in nodes for j in nodes if i != j)
    model.setObjective(obj, GRB.MINIMIZE)

    # Out-degree constraints: sum_j x_i_j = 1 for all i
    for i in nodes:
        model.addConstr(gp.quicksum(x[f"x_{i}_{j}"] for j in nodes if j != i) == 1)

    # In-degree constraints: sum_i x_i_j = 1 for all j
    for j in nodes:
        model.addConstr(gp.quicksum(x[f"x_{i}_{j}"] for i in nodes if i != j) == 1)

    # MTZ subtour elimination: for i,j in 2..N, i != j
    for i in range(2, N + 1):
        for j in range(2, N + 1):
            if i != j:
                model.addConstr(u[f"u_{i}"] - u[f"u_{j}"] + N * x[f"x_{i}_{j}"] <= N - 1)

    model.update()
    return model, variables

def _status_to_string(st) -> str:
    if st == GRB.OPTIMAL:
        return "OPTIMAL"
    if st == GRB.INFEASIBLE:
        return "INFEASIBLE"
    if st == GRB.UNBOUNDED:
        return "UNBOUNDED"
    if st == GRB.INF_OR_UNBD:
        return "INF_OR_UNBD"
    if st == GRB.TIME_LIMIT:
        return "TIME_LIMIT"
    if st == GRB.SOLUTION_LIMIT:
        return "SOLUTION_LIMIT"
    if st == GRB.CUTOFF:
        return "CUTOFF"
    return str(st)

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_str = _status_to_string(model.Status)
    objective = float(model.ObjVal)

    # Build solution dictionary with all variable values
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }