import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    container_ids = data["container_ids"]
    goods = data["goods"]  # expect order like ["A","B","C","D","E"]
    totals = data["quantity"]
    weights = data["weight_tons"]
    capacity = data["container_capacity_tons"]
    min_load = data["minimum_load_tons_if_used"]
    min_D = data["minimum_D_units_if_used"]

    # A total quantity (used for linking A/C)
    A_total = totals["A"]

    # Decision variables
    y_vars = {}   # y_i: container i used
    uA_vars = {}  # uA_i: container i loads any A goods
    q_vars = {}   # q_i_g: units of good g in container i

    n_containers = len(container_ids)

    for idx in range(1, n_containers + 1):
        y = model.addVar(vtype=GRB.BINARY, name=f"y_{idx}")
        y_vars[idx] = y

        uA = model.addVar(vtype=GRB.BINARY, name=f"uA_{idx}")
        uA_vars[idx] = uA

        for g in goods:
            ub = totals[g]
            q = model.addVar(vtype=GRB.INTEGER, lb=0, ub=ub, name=f"q_{idx}_{g}")
            q_vars[(idx, g)] = q

    model.update()

    # Constraints: total packed equals totals for each good
    for g in goods:
        model.addConstr(gp.quicksum(q_vars[(i, g)] for i in range(1, n_containers + 1)) == totals[g],
                        name=f"total_{g}")

    # Container capacity and minimum load constraints
    for i in range(1, n_containers + 1):
        sum_wq = gp.quicksum(weights[g] * q_vars[(i, g)] for g in goods)

        model.addConstr(sum_wq <= capacity * y_vars[i], name=f"cap_le_{i}")
        model.addConstr(sum_wq >= min_load * y_vars[i], name=f"cap_ge_{i}")

        # Minimum D units if container is used
        model.addConstr(q_vars[(i, "D")] >= min_D * y_vars[i], name=f"minD_{i}")

        # A/C relationship: if A is loaded, C must be loaded as well
        model.addConstr(q_vars[(i, "A")] <= A_total * uA_vars[i], name=f"qA_le_uA_{i}")
        model.addConstr(q_vars[(i, "A")] >= uA_vars[i], name=f"qA_ge_uA_{i}")
        model.addConstr(q_vars[(i, "C")] >= uA_vars[i], name=f"qC_ge_uA_{i}")

    # Objective: minimize number of used containers
    model.setObjective(gp.quicksum(y_vars[i] for i in range(1, n_containers + 1)), GRB.MINIMIZE)

    # Prepare the exact variables dict to return
    variables = {}
    for i in range(1, n_containers + 1):
        variables[f"y_{i}"] = y_vars[i]
        variables[f"uA_{i}"] = uA_vars[i]
        for g in goods:
            variables[f"q_{i}_{g}"] = q_vars[(i, g)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    # Map statuses to strings
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED",
        GRB.NODELIMIT: "NODE_LIMIT",
        GRB.ITERATION_LIMIT: "ITERATION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.NUMERIC: "NUMERIC"
    }

    stat = model.Status
    status_str = status_map.get(stat, f"Status_{stat}")

    objective = model.ObjVal if model.ObjVal is not None else 0

    goods = data["goods"]

    solution = {}
    # y and uA
    for i in range(1, len(data["container_ids"]) + 1):
        solution[f"y_{i}"] = int(variables[f"y_{i}"].X)
        solution[f"uA_{i}"] = int(variables[f"uA_{i}"].X)

    # q variables
    for i in range(1, len(data["container_ids"]) + 1):
        for g in goods:
            solution[f"q_{i}_{g}"] = int(variables[f"q_{i}_{g}"].X)

    return {
        "status": status_str,
        "objective": int(objective),
        "solution": solution
    }