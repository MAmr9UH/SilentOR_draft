import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    batches = data.get("batches", [])
    vats = data.get("vats", [])
    n_batches = len(batches)
    n_vats = len(vats)

    # Processing times p[i][j], i in 1..n_batches, j in 1..n_vats
    p = {}
    for i in range(1, n_batches + 1):
        p[i] = {}
        for j in range(1, n_vats + 1):
            p[i][j] = float(data["processing_time"][str(i)][str(j)])

    # Decision variables: y[i,j] = 1 if batch i is placed in position j
    y = {}
    for i in range(1, n_batches + 1):
        for k in range(1, n_batches + 1):
            y[(i, k)] = m.addVar(vtype=GRB.BINARY, name=f"y_{i}_{k}")

    # Completion times C[k][j]: completion time of the k-th position on vat j
    C = {}
    for k in range(1, n_batches + 1):
        for j in range(1, n_vats + 1):
            C[(k, j)] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"C_{k}_{j}")

    # Makespan variable
    Cmax = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="Cmax")

    # Helper to access p
    def P(i, j):
        return p[i][j]

    # Constraints: each batch in exactly one position
    for i in range(1, n_batches + 1):
        m.addConstr(gp.quicksum(y[(i, k)] for k in range(1, n_batches + 1)) == 1)

    # Constraints: each position occupied by exactly one batch
    for k in range(1, n_batches + 1):
        m.addConstr(gp.quicksum(y[(i, k)] for i in range(1, n_batches + 1)) == 1)

    # C_1_1 = sum_i p[i,1] * y_i1
    m.addConstr(C[(1, 1)] == gp.quicksum(P(i, 1) * y[(i, 1)] for i in range(1, n_batches + 1)))

    # C_k1 recurrence: C_k1 = C_(k-1)1 + sum_i p[i,1] * y_i,k
    for k in range(2, n_batches + 1):
        m.addConstr(C[(k, 1)] == C[(k - 1, 1)] + gp.quicksum(P(i, 1) * y[(i, k)] for i in range(1, n_batches + 1)))

    # Temporary start times for machine 2 and 3
    s2 = {}
    s3 = {}

    # Machine 2
    for k in range(1, n_batches + 1):
        s2[k] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"S_{k}_2")

    # C_k2 = s2_k + sum_i p[i,2] * y_i,k
    m.addConstr(C[(1, 2)] == s2[1] + gp.quicksum(P(i, 2) * y[(i, 1)] for i in range(1, n_batches + 1)))
    m.addConstr(s2[1] >= C[(1, 1)])

    for k in range(2, n_batches + 1):
        m.addConstr(C[(k, 2)] == s2[k] + gp.quicksum(P(i, 2) * y[(i, k)] for i in range(1, n_batches + 1)))
        m.addConstr(s2[k] >= C[(k, 1)])
        m.addConstr(s2[k] >= C[(k - 1, 2)])

    # Machine 3
    for k in range(1, n_batches + 1):
        s3[k] = m.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"S_{k}_3")

    m.addConstr(C[(1, 3)] == s3[1] + gp.quicksum(P(i, 3) * y[(i, 1)] for i in range(1, n_batches + 1)))
    m.addConstr(s3[1] >= C[(1, 2)])

    for k in range(2, n_batches + 1):
        m.addConstr(C[(k, 3)] == s3[k] + gp.quicksum(P(i, 3) * y[(i, k)] for i in range(1, n_batches + 1)))
        m.addConstr(s3[k] >= C[(k, 2)])
        m.addConstr(s3[k] >= C[(k - 1, 3)])

    # Makespan linkage
    m.addConstr(Cmax == C[(n_batches, 3)])

    # Objective
    m.setObjective(Cmax, GRB.MINIMIZE)

    # Prepare return dictionary of variables with exact keys
    variables = {}

    # y variables
    for i in range(1, n_batches + 1):
        for k in range(1, n_batches + 1):
            variables[f"y_{i}_{k}"] = y[(i, k)]

    # C variables
    for k in range(1, n_batches + 1):
        for j in range(1, n_vats + 1):
            variables[f"C_{k}_{j}"] = C[(k, j)]

    variables["Cmax"] = Cmax

    m.update()
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    model.update()

    # Objective value
    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary
    solution = {}

    # y variables values
    n_batches = len(data.get("batches", []))
    for i in range(1, n_batches + 1):
        for k in range(1, n_batches + 1):
            key = f"y_{i}_{k}"
            solution[key] = float(variables[key].X)

    # C variables values
    n_vats = len(data.get("vats", []))
    for k in range(1, n_batches + 1):
        for j in range(1, n_vats + 1):
            key = f"C_{k}_{j}"
            solution[key] = float(variables[key].X)

    # Cmax
    solution["Cmax"] = float(variables["Cmax"].X)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }