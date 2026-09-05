import gurobipy as gp

def build_model(data: dict) -> tuple:
    products = data["products"]
    quarters = data["quarters"]
    capacity = data["capacity_hours_per_quarter"]

    model = gp.Model()

    # Decision variables
    variables = {}

    # Production variables x_P_Q
    for P in products:
        for Q in quarters:
            key = f"x_{P}_{Q}"
            variables[key] = model.addVar(lb=0.0, name=key)

    # Ending inventory variables Iv_P_Q
    for P in products:
        for Q in quarters:
            key = f"Iv_{P}_{Q}"
            variables[key] = model.addVar(lb=0.0, name=key)

    # Backlog variables Bk_P_Q
    for P in products:
        for Q in quarters:
            key = f"Bk_{P}_{Q}"
            variables[key] = model.addVar(lb=0.0, name=key)

    model.update()

    # Objective: Minimize storage costs + late penalties
    storage_cost = data["storage_cost_per_unit_per_quarter"]
    penalties = data["late_penalty_per_unit_per_quarter"]

    objective = gp.quicksum(
        storage_cost * variables[f"Iv_{P}_{Q}"] +
        penalties[P] * variables[f"Bk_{P}_{Q}"]
        for P in products for Q in quarters
    )
    model.setObjective(objective, gp.GRB.MINIMIZE)

    # Constraints

    # Hours capacity per quarter
    hours_per_unit = data["hours_per_unit"]
    for Q in quarters:
        model.addConstr(
            gp.quicksum(hours_per_unit[P] * variables[f"x_{P}_{Q}"] for P in products) <= capacity
        )

    # Product I cannot be produced in quarter 2
    model.addConstr(variables["x_I_2"] == 0)

    # End-of-quarter inventory requirement: Iv_P_4 >= required_ending_inventory
    required_ending_inventory = data["required_ending_inventory"]
    for P in products:
        model.addConstr(variables[f"Iv_{P}_4"] >= required_ending_inventory)

    # Balances: Iv_P_Q - Bk_P_Q = (Iv_P_{Q-1} - Bk_P_{Q-1}) + x_P_Q - D_P_Q
    orders = data["orders"]  # mapping "P_Q" -> demand
    for P in products:
        for idx, Q in enumerate(quarters, start=1):
            Dval = orders[f"{P}_{Q}"]

            left = variables[f"Iv_{P}_{Q}"] - variables[f"Bk_{P}_{Q}"]
            if Q == 1:
                rhs = variables[f"x_{P}_{Q}"] - Dval
            else:
                rhs = (variables[f"Iv_{P}_{Q-1}"] - variables[f"Bk_{P}_{Q-1}"]) + variables[f"x_{P}_{Q}"] - Dval

            model.addConstr(left == rhs)

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    if status_code == gp.GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == gp.GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == gp.GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == gp.GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == gp.GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal)

    solution = {}
    products = data["products"]
    quarters = data["quarters"]

    for P in products:
        for Q in quarters:
            solution[f"x_{P}_{Q}"] = float(variables[f"x_{P}_{Q}"].X)

    for P in products:
        for Q in quarters:
            solution[f"Iv_{P}_{Q}"] = float(variables[f"Iv_{P}_{Q}"].X)

    for P in products:
        for Q in quarters:
            solution[f"Bk_{P}_{Q}"] = float(variables[f"Bk_{P}_{Q}"].X

            )

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }