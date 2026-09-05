import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Initialize model
    model = gp.Model()
    nodes = data.get("nodes", [])
    start_node = data.get("start_node", 1)
    dist = data.get("distance", {})
    n = len(nodes)

    # Create variable container with exact keys required
    variables = {}

    # x_i_j binary variables for all i != j
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            v = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = v

    # MTZ order variables u_i for i in 2..n (i != start_node)
    for i in nodes:
        if i == start_node:
            continue
        key = f"u_{i}"
        v = model.addVar(vtype=GRB.INTEGER, name=key, lb=2, ub=n)
        variables[key] = v

    model.update()

    # Objective: minimize total distance
    obj_expr = gp.quicksum(dist.get(f"{i},{j}", 0) * variables[f"x_{i}_{j}"]
                           for i in nodes for j in nodes if i != j)
    model.setObjective(obj_expr, GRB.MINIMIZE)

    # Out-degree constraints: each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(gp.quicksum(variables[f"x_{i}_{j}"] for j in nodes if i != j) == 1,
                        name=f"out_{i}")

    # In-degree constraints: each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(gp.quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1,
                        name=f"in_{j}")

    # MTZ subtour elimination constraints for i != start_node and j != start_node, i != j
    for i in nodes:
        if i == start_node:
            continue
        for j in nodes:
            if j == start_node or i == j:
                continue
            model.addConstr(variables[f"u_{i}"] - variables[f"u_{j}"] + n * variables[f"x_{i}_{j}"] <= n - 1,
                            name=f"mtz_{i}_{j}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(stat, str(stat))

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with exactly the required keys
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }