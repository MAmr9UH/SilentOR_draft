import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    batches = list(data["batches"])
    vats = list(data["vats"])
    positions = list(data["positions"])

    # Helper times: processing_time[b][m]
    processing_time = {}
    for b in batches:
        row = data["processing_time"][str(b)]
        for m in vats:
            processing_time[(b, m)] = row[str(m)]

    model = gp.Model()

    # Decision variables
    y = {}  # y_b_p: batch b at position p
    for b in batches:
        for p in positions:
            y[(b, p)] = model.addVar(vtype=GRB.BINARY, name=f"y_{b}_{p}")

    C = {}  # C_m_p: completion time of operation at position p on machine m
    for m in vats:
        for p in positions:
            C[(m, p)] = model.addVar(vtype=GRB.CONTINUOUS, name=f"C_{m}_{p}", lb=0.0)

    Cmax = model.addVar(vtype=GRB.CONTINUOUS, name="Cmax", lb=0.0)

    model.update()

    # Constraints: each batch assigned to exactly one position
    for b in batches:
        model.addConstr(quicksum(y[(b, p)] for p in positions) == 1, name=f"one_pos_batch_{b}")

    # Constraints: each position has exactly one batch
    for p in positions:
        model.addConstr(quicksum(y[(b, p)] for b in batches) == 1, name=f"one_batch_at_pos_{p}")

    # Flow shop constraints translated to C variables
    for m in vats:
        for p in positions:
            total_p = quicksum(processing_time[(b, m)] * y[(b, p)] for b in batches)
            # Constraint from previous position on same machine
            if p == 1:
                model.addConstr(C[(m, p)] >= total_p, name=f"C_ge_prevPos_m{m}_p{p}")
            else:
                model.addConstr(C[(m, p)] >= C[(m, p - 1)] + total_p, name=f"C_ge_prevPos_m{m}_p{p}")
            # Constraint from previous machine on same position
            if m == 1:
                model.addConstr(C[(m, p)] >= total_p, name=f"C_ge_prevMachine_m{m}_p{p}")
            else:
                model.addConstr(C[(m, p)] >= C[(m - 1, p)] + total_p, name=f"C_ge_prevMachine_m{m}_p{p}")

    # Makespan: Cmax is the maximum of all C_m_p
    for m in vats:
        for p in positions:
            model.addConstr(Cmax >= C[(m, p)], name=f"Cmax_ge_C_{m}_{p}")

    # Objective: minimize makespan
    model.setObjective(Cmax, GRB.MINIMIZE)

    # Prepare variables dictionary to return
    variables = {}
    for b in batches:
        for p in positions:
            variables[f"y_{b}_{p}"] = y[(b, p)]
    for m in vats:
        for p in positions:
            variables[f"C_{m}_{p}"] = C[(m, p)]
    variables["Cmax"] = Cmax

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status interpretation
    stat = model.Status
    if stat == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif stat == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    elif stat == GRB.INTERRUPTED:
        status = "INTERRUPTED"
    elif stat == GRB.PRIMAL_INFEASIBLE:
        status = "PRIMAL_INFEASIBLE"
    elif stat == GRB.SUBOPTIMAL:
        status = "SUBOPTIMAL"
    elif stat == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif stat == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    else:
        status = str(stat)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values
    solution = {}

    batches = list(data["batches"])
    positions = list(data["positions"])
    vats = list(data["vats"])

    for b in batches:
        for p in positions:
            key = f"y_{b}_{p}"
            solution[key] = float(variables[key].X)

    for m in vats:
        for p in positions:
            key = f"C_{m}_{p}"
            solution[key] = float(variables[key].X)

    solution["Cmax"] = float(variables["Cmax"].X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }