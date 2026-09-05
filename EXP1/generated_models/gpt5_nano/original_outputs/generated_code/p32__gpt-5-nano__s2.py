import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    batches = list(data["batches"])
    positions = list(data["positions"])
    vats = list(data["vats"])

    # Processing times: proc[i][v] for batch i and vat v
    proc = {i: {v: 0.0 for v in vats} for i in batches}
    for i_str, inner in data["processing_time"].items():
        i = int(i_str)
        for v_str, t in inner.items():
            v = int(v_str)
            proc[i][v] = float(t)

    model = gp.Model()

    # Variables
    y = {}  # y[i,p] = 1 if batch i is placed at position p
    for i in batches:
        for p in positions:
            y[(i, p)] = model.addVar(vtype=GRB.BINARY, name=f"y_{i}_{p}")

    C = {}  # C[p,v] = completion time of position p on vat v
    for p in positions:
        for v in vats:
            C[(p, v)] = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name=f"C_{p}_{v}")

    Cmax = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="Cmax")

    model.update()

    # Permutation constraints: each batch exactly one position
    for i in batches:
        model.addConstr(gp.quicksum(y[(i, p)] for p in positions) == 1, name=f"perm_batch_{i}")

    # Each position exactly one batch
    for p in positions:
        model.addConstr(gp.quicksum(y[(i, p)] for i in batches) == 1, name=f"perm_position_{p}")

    # Flow constraints across machines along the same position
    for p in positions:
        # On vat 1
        model.addConstr(C[(p, 1)] >= gp.quicksum(proc[i][1] * y[(i, p)] for i in batches),
                        name=f"flow_p{p}_v1")
        # On vat 2
        model.addConstr(C[(p, 2)] >= C[(p, 1)] + gp.quicksum(proc[i][2] * y[(i, p)] for i in batches),
                        name=f"flow_p{p}_v2")
        # On vat 3
        model.addConstr(C[(p, 3)] >= C[(p, 2)] + gp.quicksum(proc[i][3] * y[(i, p)] for i in batches),
                        name=f"flow_p{p}_v3")

    # Monotonicity of completion times along positions on each vat
    for v in vats:
        for idx in range(2, len(positions) + 1):
            p = positions[idx - 1]
            p_prev = positions[idx - 2]
            model.addConstr(C[(p, v)] >= C[(p_prev, v)], name=f"mono_p{p}_v{v}")

    # Cmax bounds
    for p in positions:
        for v in vats:
            model.addConstr(C[(p, v)] <= Cmax, name=f"Cmax_bound_p{p}_v{v}")

    model.setObjective(Cmax, GRB.MINIMIZE)

    variables = {}
    for i in batches:
        for p in positions:
            variables[f"y_{i}_{p}"] = y[(i, p)]
    for p in positions:
        for v in vats:
            variables[f"C_{p}_{v}"] = C[(p, v)]
    variables["Cmax"] = Cmax

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with all required keys
    solution = {}

    # y variables
    for i in data["batches"]:
        for p in data["positions"]:
            key = f"y_{i}_{p}"
            solution[key] = variables[key].X

    # C variables
    for p in data["positions"]:
        for v in data["vats"]:
            key = f"C_{p}_{v}"
            solution[key] = variables[key].X

    solution["Cmax"] = variables["Cmax"].X

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }