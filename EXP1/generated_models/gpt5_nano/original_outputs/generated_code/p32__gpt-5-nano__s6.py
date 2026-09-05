import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model("FlowShop3x5")
    batches = list(data["batches"])
    positions = list(data["positions"])
    vats = list(data["vats"])

    # Build processing times dictionary: times[i][j]
    times = {}
    for i in batches:
        times[i] = {}
        for j in vats:
            times[i][j] = data["processing_time"][str(i)][str(j)]

    # Create variables
    variables = {}

    # y_{i}_{p} binary: batch i in position p
    for i in batches:
        for p in positions:
            key = f"y_{i}_{p}"
            variables[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    # C_{p}_{j} continuous: completion time of position p on vat j
    for p in positions:
        for j in vats:
            key = f"C_{p}_{j}"
            variables[key] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=key)

    # Cmax
    variables["Cmax"] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name="Cmax")

    model.update()

    # 1) Permutation constraints: each batch in exactly one position
    for i in batches:
        model.addConstr(gp.quicksum(variables[f"y_{i}_{p}"] for p in positions) == 1)

    # 2) Each position holds exactly one batch
    for p in positions:
        model.addConstr(gp.quicksum(variables[f"y_{i}_{p}"] for i in batches) == 1)

    # 3) Flow constraints for each position p and vat j
    for p in positions:
        for j in vats:
            expr = gp.quicksum(times[i][j] * variables[f"y_{i}_{p}"] for i in batches)
            if p == 1 and j == 1:
                model.addConstr(variables[f"C_{p}_{j}"] >= expr)
            elif p == 1 and j > 1:
                model.addConstr(variables[f"C_{p}_{j}"] >= variables[f"C_{p}_{j-1}"] + expr)
            elif p > 1 and j == 1:
                model.addConstr(variables[f"C_{p}_{j}"] >= variables[f"C_{p-1}_{j}"] + expr)
            else:
                model.addConstr(variables[f"C_{p}_{j}"] >= variables[f"C_{p-1}_{j}"] + expr)
                model.addConstr(variables[f"C_{p}_{j}"] >= variables[f"C_{p}_{j-1}"] + expr)

    # 4) Cmax >= all C_{p}_{j}
    for p in positions:
        for j in vats:
            model.addConstr(variables["Cmax"] >= variables[f"C_{p}_{j}"])

    # Objective: minimize makespan
    model.setObjective(variables["Cmax"], gp.GRB.MINIMIZE)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    from gurobipy import GRB

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    for i in data["batches"]:
        for p in data["positions"]:
            solution[f"y_{i}_{p}"] = float(variables[f"y_{i}_{p}"].X)

    for p in data["positions"]:
        for j in data["vats"]:
            solution[f"C_{p}_{j}"] = float(variables[f"C_{p}_{j}"].X)

    solution["Cmax"] = float(variables["Cmax"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective,
        "solution": solution
    }