from gurobipy import Model, GRB, quicksum

def build_model(data: dict) -> tuple:
    nodes = data["nodes"]
    n = len(nodes)
    dist = data["distance"]
    m = data.get("mtz_big_m", n)

    model = Model()

    variables = {}

    # x_i_j variables for all i != j
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # MTZ order variables u_i for i = 2..n
    for i in range(2, n + 1):
        key = f"u_{i}"
        # MTZ requires integer order between 2 and n (inclusive)
        variables[key] = model.addVar(vtype=GRB.INTEGER, name=key, lb=2, ub=m)

    # Objective: minimize sum distance(i,j) * x_i_j
    obj = quicksum(dist.get(f"{i},{j}", 0) * variables[f"x_{i}_{j}"]
                   for i in nodes for j in nodes if i != j)
    model.setObjective(obj, GRB.MINIMIZE)

    # Out-degree constraints: each node has exactly one outgoing arc
    for i in nodes:
        model.addConstr(quicksum(variables[f"x_{i}_{j}"] for j in nodes if i != j) == 1,
                        name=f"out_{i}")

    # In-degree constraints: each node has exactly one incoming arc
    for j in nodes:
        model.addConstr(quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1,
                        name=f"in_{j}")

    # MTZ subtour elimination constraints
    for i in range(2, n + 1):
        for j in range(2, n + 1):
            if i == j:
                continue
            model.addConstr(variables[f"u_{i}"] - variables[f"u_{j}"] + m * variables[f"x_{i}_{j}"] <= m - 1,
                            name=f"mtz_{i}_{j}")

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    from gurobipy import GRB
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status = status_map.get(model.Status, str(model.Status))
    objective = model.ObjVal

    solution = {k: variables[k].X for k in variables.keys()}

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }