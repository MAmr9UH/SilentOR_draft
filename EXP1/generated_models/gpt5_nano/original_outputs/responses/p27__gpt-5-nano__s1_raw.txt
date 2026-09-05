import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    nodes = data.get("nodes", [])
    n = len(nodes)
    dist = data.get("distance", {})
    
    model = gp.Model()
    model.Params.OutputFlag = 0  # suppress solver output

    # Decision variables
    variables = {}

    # x_i_j: binary, for all i != j
    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            key = f"x_{i}_{j}"
            var = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = var

    # u_i: MTZ order variables for i != 1 (depot)
    for i in nodes:
        if i == 1:
            continue
        key = f"u_{i}"
        var = model.addVar(vtype=GRB.INTEGER, lb=2, ub=n, name=key)
        variables[key] = var

    model.update()

    # Objective: minimize total distance
    objective = quicksum(dist[f"{i},{j}"] * variables[f"x_{i}_{j}"]
                         for i in nodes for j in nodes if i != j)
    model.setObjective(objective, GRB.MINIMIZE)

    # Constraints
    # 1) Outgoing degree: sum_j x_i_j = 1 for all i
    for i in nodes:
        model.addConstr(
            quicksum(variables[f"x_{i}_{j}"] for j in nodes if j != i) == 1,
            name=f"out_{i}"
        )

    # 2) Incoming degree: sum_i x_i_j = 1 for all j
    for j in nodes:
        model.addConstr(
            quicksum(variables[f"x_{i}_{j}"] for i in nodes if i != j) == 1,
            name=f"in_{j}"
        )

    # 3) MTZ subtour elimination: for i != 1, j != 1, i != j
    for i in nodes:
        if i == 1:
            continue
        for j in nodes:
            if j == 1 or i == j:
                continue
            model.addConstr(
                variables[f"u_{i}"] - variables[f"u_{j}"] + n * variables[f"x_{i}_{j}"] <= n - 1,
                name=f"mtz_{i}_{j}"
            )

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status interpretation
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    # Build solution dictionary with required keys
    solution = {}

    # x variables
    x_keys = [f"x_1_2", "x_1_3", "x_1_4", "x_1_5", "x_1_6", "x_1_7",
              "x_2_1", "x_2_3", "x_2_4", "x_2_5", "x_2_6", "x_2_7",
              "x_3_1", "x_3_2", "x_3_4", "x_3_5", "x_3_6", "x_3_7",
              "x_4_1", "x_4_2", "x_4_3", "x_4_5", "x_4_6", "x_4_7",
              "x_5_1", "x_5_2", "x_5_3", "x_5_4", "x_5_6", "x_5_7",
              "x_6_1", "x_6_2", "x_6_3", "x_6_4", "x_6_5", "x_6_7",
              "x_7_1", "x_7_2", "x_7_3", "x_7_4", "x_7_5", "x_7_6"]
    for k in x_keys:
        v = variables[k]
        solution[k] = float(v.X)

    # u variables
    for i in range(2, 8):
        key = f"u_{i}"
        solution[key] = float(variables[key].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }