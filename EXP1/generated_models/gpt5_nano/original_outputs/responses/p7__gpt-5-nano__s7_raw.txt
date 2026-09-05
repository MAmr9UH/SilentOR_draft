import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    products = data["products"]
    quarters = data["quarters"]
    orders = data["orders"]  # keys like "I_1", "II_3", etc.
    hours_per_unit = data["hours_per_unit"]  # dict: {"I": 2, "II": 4, "III": 3}
    capacity = data["capacity_hours_per_quarter"]
    initial_inventory = data["initial_inventory"]
    required_ending_inventory = data["required_ending_inventory"]
    late_penalty = data["late_penalty_per_unit_per_quarter"]  # dict: {"I": 20, "II": 20, "III": 10}
    storage_cost = data["storage_cost_per_unit_per_quarter"]
    blocked_quarter_for_I = data["product_I_blocked_quarter"]

    model = gp.Model()

    # Create variables
    variables = {}

    # Production variables x_P_Q
    for P in products:
        for Q in quarters:
            key = f"x_{P}_{Q}"
            # Product I cannot be produced in quarter 2
            if P == "I" and Q == 2:
                var = model.addVar(lb=0, ub=0, name=key)
            else:
                var = model.addVar(lb=0, name=key)
            variables[key] = var

    # Ending inventory Iv_P_Q
    for P in products:
        for Q in quarters:
            key = f"Iv_{P}_{Q}"
            var = model.addVar(lb=0, name=key)
            variables[key] = var

    # Backlog Bk_P_Q
    for P in products:
        for Q in quarters:
            key = f"Bk_{P}_{Q}"
            var = model.addVar(lb=0, name=key)
            variables[key] = var

    model.update()

    # Constraints
    # 1) Inventory balance with backlog: Iv_P_Q = Iv_P_(Q-1) + x_P_Q - D_P_Q + Bk_P_Q
    for P in products:
        for Q in quarters:
            D_val = orders[f"{P}_{Q}"]
            Iv_Q = variables[f"Iv_{P}_{Q}"]
            x_Q = variables[f"x_{P}_{Q}"]
            Bk_Q = variables[f"Bk_{P}_{Q}"]
            if Q == 1:
                Iv_prev = initial_inventory
            else:
                Iv_prev = variables[f"Iv_{P}_{Q-1}"]
            model.addConstr(Iv_Q == Iv_prev + x_Q - D_val + Bk_Q)

    # 2) Backlog cannot exceed demand: Bk_P_Q <= D_P_Q
    for P in products:
        for Q in quarters:
            D_val = orders[f"{P}_{Q}"]
            Bk_Q = variables[f"Bk_{P}_{Q}"]
            model.addConstr(Bk_Q <= D_val)

    # 3) End-of-quarter inventory must be required ending inventory at Q=4
    for P in products:
        Iv_4 = variables[f"Iv_{P}_4"]
        model.addConstr(Iv_4 == required_ending_inventory)

    # 4) Production hour capacity per quarter
    for Q in quarters:
        expr = gp.quicksum(hours_per_unit[P] * variables[f"x_{P}_{Q}"] for P in products)
        model.addConstr(expr <= capacity)

    # Objective: minimize storage cost + late penalties
    storage_term = gp.quicksum(storage_cost * variables[f"Iv_{P}_{Q}"] for P in products for Q in quarters)
    penalty_term = gp.quicksum(late_penalty[P] * variables[f"Bk_{P}_{Q}"] for P in products for Q in quarters)
    model.setObjective(storage_term + penalty_term, GRB.MINIMIZE)

    model.update()

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
    obj_val = float(model.ObjVal) if model.Status == GRB.OPTIMAL else float("nan")

    # Build solution dict
    solution = {}

    # x_P_Q
    for P in data["products"]:
        for Q in data["quarters"]:
            key = f"x_{P}_{Q}"
            solution[key] = float(variables[key].X)

    # Iv_P_Q
    for P in data["products"]:
        for Q in data["quarters"]:
            key = f"Iv_{P}_{Q}"
            solution[key] = float(variables[key].X)

    # Bk_P_Q
    for P in data["products"]:
        for Q in data["quarters"]:
            key = f"Bk_{P}_{Q}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }