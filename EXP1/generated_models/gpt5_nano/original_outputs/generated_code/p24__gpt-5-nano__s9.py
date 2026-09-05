import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model and a dictionary of variables according to the required schema.
    """
    model = gp.Model()

    container_ids = data.get("container_ids", [])
    max_containers = data.get("max_containers_available", len(container_ids))
    # Parameters
    weight = data.get("weight_tons", {})
    capacity = data.get("container_capacity_tons", 0)
    min_load = data.get("minimum_load_tons_if_used", 0)
    min_D_units = data.get("minimum_D_units_if_used", 0)
    quantities = data.get("quantity", {})
    goods = data.get("goods", ["A","B","C","D","E"])
    total_A = quantities.get("A", 0)

    # Variable container usage y_i for i = 1..10
    y = {}
    # A presence indicator per container
    uA = {}
    # q_i_g variables: units of good g in container i
    q = {}

    variables = {}

    # Create y_i and uA_i for containers 1..10
    for idx in range(1, 11):
        y_var = model.addVar(vtype=GRB.BINARY, name=f"y_{idx}")
        y[idx] = y_var
        variables[f"y_{idx}"] = y_var

        uA_var = model.addVar(vtype=GRB.BINARY, name=f"uA_{idx}")
        uA[idx] = uA_var
        variables[f"uA_{idx}"] = uA_var

    # Create q_i_g for i=1..10 and g in A..E
    for i in range(1, 11):
        for g in goods:
            var = model.addVar(vtype=GRB.INTEGER, name=f"q_{i}_{g}", lb=0)
            q[(i, g)] = var
            variables[f"q_{i}_{g}"] = var

    model.update()

    # Objective: minimize number of containers used
    model.setObjective(gp.quicksum(y[i] for i in range(1, 11)), GRB.MINIMIZE)

    # Supply constraints: total units for each good must match available quantity
    for g in goods:
        total_qty = quantities.get(g, 0)
        model.addConstr(gp.quicksum(q[(i, g)] for i in range(1, 11)) == total_qty, name=f"total_{g}")

    A_total_qty = total_A

    # Container capacity and minimum load constraints, and D minimum per used container
    for i in range(1, 11):
        weight_sum = gp.quicksum(weight[g] * q[(i, g)] for g in goods)

        # Capacity: if container not used, sum must be 0
        model.addConstr(weight_sum <= capacity * y[i], name=f"cap_{i}")

        # Minimum load if used
        model.addConstr(weight_sum >= min_load * y[i], name=f"minload_{i}")

        # Minimum D units if used
        model.addConstr(q[(i, "D")] >= min_D_units * y[i], name=f"minD_{i}")

        # A/C rule: if any A loaded in container i, at least one C must be loaded
        model.addConstr(q[(i, "A")] <= A_total_qty * uA[i], name=f"A_presence_cap_{i}")
        model.addConstr(q[(i, "A")] >= uA[i], name=f"A_presence_lb_{i}")
        model.addConstr(q[(i, "C")] >= uA[i], name=f"C_requires_A_present_{i}")
        # A presence implies container is used
        model.addConstr(uA[i] <= y[i], name=f"uA_implies_y_{i}")

    return model, variables

def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the solution in the required schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Helper to convert status to string
    status_code = model.Status
    def _status_to_string(code: int) -> str:
        if code == GRB.OPTIMAL:
            return "OPTIMAL"
        if code == GRB.INFEASIBLE:
            return "INFEASIBLE"
        if code == GRB.UNBOUNDED:
            return "UNBOUNDED"
        if code == GRB.INF_OR_UNBD:
            return "INF_OR_UNBD"
        if code == GRB.TIME_LIMIT:
            return "TIME_LIMIT"
        return str(code)

    status_str = _status_to_string(status_code)

    # Objective value
    obj_val = float(model.ObjVal) if model.SolCount > 0 else float('nan')

    # Build solution dict with exact keys
    solution = {}

    # y_1 .. y_10
    for i in range(1, 11):
        solution[f"y_{i}"] = float(variables[f"y_{i}"].X)

    # uA_1 .. uA_10
    for i in range(1, 11):
        solution[f"uA_{i}"] = float(variables[f"uA_{i}"].X)

    # q_i_G for i=1..10, G in A..E
    goods = ["A","B","C","D","E"]
    for i in range(1, 11):
        for g in goods:
            solution[f"q_{i}_{g}"] = int(variables[f"q_{i}_{g}"].X)

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }