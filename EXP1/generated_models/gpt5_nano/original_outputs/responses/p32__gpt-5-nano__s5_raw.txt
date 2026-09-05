import sys
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = __import__("gurobipy").Model("FlowShopPermutation")
    batches = data["batches"]
    positions = data["positions"]
    vats = data["vats"]
    times = data["processing_time"]

    # Decision variables
    y = {}
    for i in batches:
        for p in positions:
            y[(i, p)] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{p}")

    C = {}
    for p in positions:
        for v in vats:
            C[(p, v)] = model.addVar(vtype=GRB.CONTINUOUS, name=f"C_{p}_{v}")

    # Max-linearization deltas for max terms
    d2 = {}  # for max on machine 2
    d3 = {}  # for max on machine 3
    M = 10000  # big-M
    for p in positions:
        if p >= 2:
            d2[p] = model.addVar(vtype=GRB.BINARY, name=f"d2_{p}")
            d3[p] = model.addVar(vtype=GRB.BINARY, name=f"d3_{p}")

    Cmax = model.addVar(vtype=GRB.CONTINUOUS, name="Cmax")

    model.update()

    # Identity constraints: each batch in exactly one position
    for i in batches:
        model.addConstr(quicksum(y[(i, p)] for p in positions) == 1)

    # Each position holds exactly one batch
    for p in positions:
        model.addConstr(quicksum(y[(i, p)] for i in batches) == 1)

    # Helper to fetch processing time
    def t(i, v):
        return times[str(i)][str(v)]

    # C_1_1
    model.addConstr(C[(1, 1)] == quicksum(t(i, 1) * y[(i, 1)] for i in batches))
    # C_1_2
    model.addConstr(C[(1, 2)] == C[(1, 1)] + quicksum(t(i, 2) * y[(i, 1)] for i in batches))
    # C_1_3
    model.addConstr(C[(1, 3)] == C[(1, 2)] + quicksum(t(i, 3) * y[(i, 1)] for i in batches))

    # C_p1 for p=2..5
    for p in [2, 3, 4, 5]:
        model.addConstr(C[(p, 1)] == C[(p - 1, 1)] + quicksum(t(i, 1) * y[(i, p)] for i in batches))

    # C_p2 and C_p3 with max-linearization
    for p in [2, 3, 4, 5]:
        A_p2 = quicksum(t(i, 2) * y[(i, p)] for i in batches)
        A_p3 = quicksum(t(i, 3) * y[(i, p)] for i in batches)

        # C_p2 = max( C_p1, C_{p-1,2} ) + A_p2
        model.addConstr(C[(p, 2)] >= C[(p, 1)] + A_p2)
        model.addConstr(C[(p, 2)] >= C[(p - 1, 2)] + A_p2)
        model.addConstr(C[(p, 2)] <= C[(p, 1)] + A_p2 + M * (1 - d2[p]))
        model.addConstr(C[(p, 2)] <= C[(p - 1, 2)] + A_p2 + M * d2[p])

        # C_p3 = max( C_p2, C_{p-1,3} ) + A_p3
        model.addConstr(C[(p, 3)] >= C[(p, 2)] + A_p3)
        model.addConstr(C[(p, 3)] >= C[(p - 1, 3)] + A_p3)
        model.addConstr(C[(p, 3)] <= C[(p, 2)] + A_p3 + M * (1 - d3[p]))
        model.addConstr(C[(p, 3)] <= C[(p - 1, 3)] + A_p3 + M * d3[p])

    # Cmax linkage
    model.addConstr(Cmax == C[(5, 3)])

    # Objective
    model.setObjective(Cmax, GRB.MINIMIZE)

    # Build variable map with exact keys
    variables = {}

    # y variables
    for i in batches:
        for p in positions:
            key = f"y_{i}_{p}"
            variables[key] = y[(i, p)]

    # C variables
    for p in positions:
        for v in vats:
            key = f"C_{p}_{v}"
            variables[key] = C[(p, v)]

    # deltas
    for p in positions:
        if p >= 2:
            variables[f"d2_{p}"] = d2[p]
            variables[f"d3_{p}"] = d3[p]

    # Cmax
    variables["Cmax"] = Cmax

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    status = model.Status
    # Map status to string
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }.get(status, str(status))

    # Ensure values are available
    model.update()
    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with exact keys
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    result = {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }
    return result