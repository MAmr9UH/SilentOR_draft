import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("ContainerPacking")

    container_ids = data.get("container_ids", [])
    max_containers = len(container_ids)
    goods = data.get("goods", [])
    quantities = data.get("quantity", {})
    weights = data.get("weight_tons", {})
    capacity = data.get("container_capacity_tons", 0.0)
    min_load = data.get("minimum_load_tons_if_used", 0.0)
    min_D_units = data.get("minimum_D_units_if_used", 0)
    A_requires_at_least_one_C = data.get("A_requires_at_least_one_C_in_same_container", True)

    # Decision variables
    variables = {}

    # y_i: container i used
    y_vars = {}
    for i in range(1, max_containers + 1):
        y = model.addVar(vtype=GRB.BINARY, name=f"y_{i}")
        y_vars[i] = y
        variables[f"y_{i}"] = y

    # uA_i: container i loads any A goods
    uA_vars = {}
    for i in range(1, max_containers + 1):
        uA = model.addVar(vtype=GRB.BINARY, name=f"uA_{i}")
        uA_vars[i] = uA
        variables[f"uA_{i}"] = uA

    # q_{i}_{g}: units of good g in container i
    q_vars = {}
    for i in range(1, max_containers + 1):
        for g in goods:
            q = model.addVar(vtype=GRB.INTEGER, lb=0, name=f"q_{i}_{g}")
            q_vars[(i, g)] = q
            variables[f"q_{i}_{g}"] = q

    model.update()

    # Quantities constraints: total per good equals data quantities
    for g in goods:
        total_g = quantities.get(g, 0)
        model.addConstr(gp.quicksum(q_vars[(i, g)] for i in range(1, max_containers + 1)) == total_g)

    # Container capacity and minimum load constraints
    for i in range(1, max_containers + 1):
        total_weight_i = gp.quicksum(weights[g] * q_vars[(i, g)] for g in goods)
        model.addConstr(total_weight_i <= capacity * y_vars[i])
        model.addConstr(total_weight_i >= min_load * y_vars[i])

        # Minimum D units if container used
        if "D" in goods:
            model.addConstr(q_vars[(i, "D")] >= min_D_units * y_vars[i])

        # A-C rule: If A is loaded in container i, at least one C must be loaded
        # Link A presence to uA_i
        M_A = quantities.get("A", 0)
        model.addConstr(q_vars[(i, "A")] <= M_A * uA_vars[i])
        model.addConstr(q_vars[(i, "A")] >= uA_vars[i])
        if A_requires_at_least_one_C:
            model.addConstr(q_vars[(i, "C")] >= uA_vars[i])

    # Objective: minimize number of used containers
    model.setObjective(gp.quicksum(y_vars[i] for i in range(1, max_containers + 1)), GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status string
    def status_to_string(status):
        if status == GRB.OPTIMAL:
            return "OPTIMAL"
        if status == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if status == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if status == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if status == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        if status == GRB.SUBOPTIMAL:
            return "SUBOPTIMAL"
        return str(status)

    status_str = status_to_string(model.Status)
    objective_val = float(model.ObjVal)

    # Build solution dictionary
    solution = {}

    # y_i and uA_i values
    for i in range(1, len(data.get("container_ids", [])) + 1):
        solution[f"y_{i}"] = variables[f"y_{i}"].X
        solution[f"uA_{i}"] = variables[f"uA_{i}"].X

    # q_i_g values
    goods = data.get("goods", [])
    for i in range(1, len(data.get("container_ids", [])) + 1):
        for g in goods:
            solution[f"q_{i}_{g}"] = variables[f"q_{i}_{g}"].X

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }