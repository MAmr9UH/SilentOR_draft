import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()

    batches = data["batches"]
    positions = data["positions"]
    vats = data["vats"]

    # Decision variables
    variables = {}

    # y_i_p: batch i at position p
    for i in batches:
        for p in positions:
            key = f"y_{i}_{p}"
            variables[key] = model.addVar(vtype=GRB.BINARY, name=key)

    # C_p_v: completion time of the batch at position p on vat v
    for p in positions:
        for v in vats:
            key = f"C_{p}_{v}"
            variables[key] = model.addVar(vtype=GRB.CONTINUOUS, name=key)

    # Cmax: makespan
    variables["Cmax"] = model.addVar(vtype=GRB.CONTINUOUS, name="Cmax")

    model.update()

    # Objective: minimize makespan
    model.setObjective(variables["Cmax"], GRB.MINIMIZE)

    # Constraints

    # Each batch is assigned to exactly one position
    for i in batches:
        model.addConstr(quicksum(variables[f"y_{i}_{p}"] for p in positions) == 1)

    # Each position has exactly one batch
    for p in positions:
        model.addConstr(quicksum(variables[f"y_{i}_{p}"] for i in batches) == 1)

    # Time for each position on each vat depends on which batch is at that position
    for p in positions:
        for v in vats:
            T_p_v = quicksum(data["processing_time"][str(i)][str(v)] * variables[f"y_{i}_{p}"] for i in batches)
            if p == 1:
                model.addConstr(variables[f"C_{p}_{v}"] >= T_p_v)
            else:
                model.addConstr(variables[f"C_{p}_{v}"] >= variables[f"C_{p-1}_{v}"] + T_p_v)
                if v > 1:
                    model.addConstr(variables[f"C_{p}_{v}"] >= variables[f"C_{p}_{v-1}"] + T_p_v)

    # Makespan constraints: Cmax >= C_p_v for all p, v
    for p in positions:
        for v in vats:
            model.addConstr(variables["Cmax"] >= variables[f"C_{p}_{v}"])

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to a readable string
    status_code = model.Status
    from gurobipy import GRB as _GRB
    if status_code == _GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == _GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == _GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == _GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    elif status_code == _GRB.SUBOPTIMAL:
        status_str = "SUBOPTIMAL"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    # Build solution dictionary with required keys
    solution = {}

    # y variables in order y_1_1 .. y_5_5
    for i in data["batches"]:
        for p in data["positions"]:
            solution[f"y_{i}_{p}"] = variables[f"y_{i}_{p}"].X

    # C_p_v in order C_1_1 .. C_5_3
    for p in data["positions"]:
        for v in data["vats"]:
            solution[f"C_{p}_{v}"] = variables[f"C_{p}_{v}"].X

    solution["Cmax"] = variables["Cmax"].X

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }