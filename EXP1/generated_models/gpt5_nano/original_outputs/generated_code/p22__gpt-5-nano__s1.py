import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Builds and returns a Gurobi model and a dictionary of decision variables.
    The returned model is not optimized here.
    """
    m = gp.Model()
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    bandwidth = data["bandwidth"]
    big_m = data.get("big_m", 100)

    # Decision variable: bottleneck bandwidth
    z = m.addVar(lb=0.0, name="z")

    # Binary variables for each positive-bandwidth directed arc
    arc_vars = {}
    for i in nodes:
        for j in nodes:
            b = bandwidth[i][j]
            if b > 0:
                var = m.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")
                arc_vars[(i, j)] = var

    m.update()

    # Objective: maximize bottleneck z
    m.setObjective(z, GRB.MAXIMIZE)

    # Flow balance constraints (A -> E) with exactly one unit of flow
    for v in nodes:
        out_sum = gp.quicksum(arc_vars[(v, w)] for w in nodes if bandwidth[v][w] > 0)
        in_sum = gp.quicksum(arc_vars[(u, v)] for u in nodes if bandwidth[u][v] > 0)
        d = 1 if v == source else -1 if v == sink else 0
        m.addConstr(out_sum - in_sum == d)

    # Capacity constraints to ensure a single path (no branching)
    for v in nodes:
        out_sum = gp.quicksum(arc_vars[(v, w)] for w in nodes if bandwidth[v][w] > 0)
        in_sum = gp.quicksum(arc_vars[(u, v)] for u in nodes if bandwidth[u][v] > 0)
        m.addConstr(out_sum <= 1)
        m.addConstr(in_sum <= 1)

    # Bottleneck constraints: z <= b + big_m * (1 - x_{i,j}) for every arc
    for (i, j), xvar in arc_vars.items():
        b = bandwidth[i][j]
        m.addConstr(z <= b + big_m * (1 - xvar))

    m.update()

    # Prepare variables dict with exactly the required keys
    variables = {"z": z}
    for (i, j), var in arc_vars.items():
        variables[f"x_{i}_{j}"] = var

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Read status
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

    model.update()
    z_val = float(variables["z"].X)

    # Build solution dictionary matching required schema
    solution = {"z": z_val}
    arc_keys = ["x_A_B","x_A_C","x_A_E","x_B_A","x_B_C","x_B_D","x_B_E",
                "x_C_A","x_C_D","x_C_E","x_D_A","x_D_B","x_D_C","x_D_E",
                "x_E_B","x_E_D"]
    for key in arc_keys:
        solution[key] = float(variables[key].X)

    # Return in the exact schema
    return {
        "type": "object",
        "status": status,
        "objective": float(z_val),
        "solution": solution
    }