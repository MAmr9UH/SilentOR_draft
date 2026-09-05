import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    batches = list(data["batches"])
    vats = list(data["vats"])
    positions = list(data["positions"])

    # Processing times t[i][m]
    processing_time = data["processing_time"]
    t = {}
    for i in batches:
        t[i] = {}
        for m in vats:
            t[i][m] = processing_time[str(i)][str(m)]

    model = gp.Model()

    # Decision variables
    # y[i,p] = 1 if batch i is placed at position p
    y = {}
    for i in batches:
        y[i] = {}
        for p in positions:
            var = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{p}")
            y[i][p] = var

    # C[p,m] = completion time of the batch at position p on vat m
    C = {}
    for p in positions:
        C[p] = {}
        for m in vats:
            C[p][m] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"C_{p}_{m}")

    # Cmax = makespan
    Cmax = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="Cmax")

    # Collect variables into a flat dict as required
    variables = {}
    for i in batches:
        for p in positions:
            variables[f"y_{i}_{p}"] = y[i][p]
    for p in positions:
        for m in vats:
            variables[f"C_{p}_{m}"] = C[p][m]
    variables["Cmax"] = Cmax

    # Constraints
    # 1) Each batch assigned to exactly one position
    for i in batches:
        model.addConstr(gp.quicksum(y[i][p] for p in positions) == 1)

    # 2) Each position has exactly one batch
    for p in positions:
        model.addConstr(gp.quicksum(y[i][p] for i in batches) == 1)

    # 3) Flow on each vat per position
    for m in vats:
        for p in positions:
            sum_t = gp.quicksum(t[i][m] * y[i][p] for i in batches)
            if p == 1:
                model.addConstr(C[p][m] >= sum_t)
            else:
                model.addConstr(C[p][m] >= C[p-1][m] + sum_t)

    # 4) Precedence across machines for same batch (through positions)
    for m in [2, 3]:
        for p in positions:
            sum_prev = gp.quicksum(t[i][m-1] * y[i][p] for i in batches)
            model.addConstr(C[p][m] >= C[p][m-1] + sum_prev)

    # 5) Makespan bounds
    for p in positions:
        for m in vats:
            model.addConstr(Cmax >= C[p][m])

    # 6) Objective
    model.setObjective(Cmax, GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(stat)

    objective = float(model.ObjVal)

    model.update()

    solution = {}
    for i in data["batches"]:
        for p in data["positions"]:
            key = f"y_{i}_{p}"
            solution[key] = float(variables[key].X)

    for p in data["positions"]:
        for m in data["vats"]:
            key = f"C_{p}_{m}"
            solution[key] = float(variables[key].X)

    solution["Cmax"] = float(variables["Cmax"].X)

    return {"status": status, "objective": objective, "solution": solution}