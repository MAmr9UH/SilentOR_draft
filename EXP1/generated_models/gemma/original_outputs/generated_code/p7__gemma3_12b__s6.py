import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    products = data["products"]
    quarters = data["quarters"]
    orders = data["orders"]
    hours_per_unit = data["hours_per_unit"]
    capacity_hours_per_quarter = data["capacity_hours_per_quarter"]
    initial_inventory = data["initial_inventory"]
    required_ending_inventory = data["required_ending_inventory"]
    late_penalty_per_unit_per_quarter = data["late_penalty_per_unit_per_quarter"]
    storage_cost_per_unit_per_quarter = data["storage_cost_per_unit_per_quarter"]
    product_I_blocked_quarter = data["product_I_blocked_quarter"]

    # Decision variables
    x = {}
    Iv = {}
    Bk = {}
    for product in products:
        for quarter in quarters:
            if product == "I" and quarter == product_I_blocked_quarter:
                model.addVar(vtype=GRB.BINARY, name=f"x_{product}_{quarter}")
            else:
                x[product, quarter] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"x_{product}_{quarter}")

    for product in products:
        for quarter in quarters:
            Iv[product, quarter] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"Iv_{product}_{quarter}")
            Bk[product, quarter] = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=f"Bk_{product}_{quarter}")

    # Objective function
    obj = gp.quicksum(
        late_penalty_per_unit_per_quarter[product] * Bk[product, quarter]
        for product in products
        for quarter in quarters
    ) + gp.quicksum(
        storage_cost_per_unit_per_quarter * x[product, quarter]
        for product in products
        for quarter in quarters
    )
    model.setObjective(obj, GRB.MINIMIZE)

    # Constraints
    # Production <= Capacity
    for quarter in quarters:
        production_hours = gp.quicksum(
            hours_per_unit[product] * x[product, quarter] for product in products
        )
        model.addConstr(production_hours <= capacity_hours_per_quarter, name=f"capacity_{quarter}")

    # Order Fulfillment
    for product in products:
        for quarter in quarters:
            if quarter == 1:
                model.addConstr(Iv[product, quarter] + x[product, quarter] >= orders[f"{product}_{quarter}"] - initial_inventory, name=f"order_{product}_{quarter}")
            else:
                model.addConstr(Iv[product, quarter] + x[product, quarter] >= orders[f"{product}_{quarter}"], name=f"order_{product}_{quarter}")

    # Inventory Flow
    for product in products:
        for quarter in quarters:
            if quarter == 1:
                model.addConstr(Iv[product, quarter] == x[product, quarter] - orders[f"{product}_{quarter}"] + initial_inventory, name=f"inventory_{product}_{quarter}")
            elif quarter == 4:
                model.addConstr(Iv[product, quarter] == required_ending_inventory, name=f"inventory_{product}_{quarter}")
            else:
                model.addConstr(Iv[product, quarter] == Iv[product, quarter - 1] + x[product, quarter] - orders[f"{product}_{quarter}"], name=f"inventory_{product}_{quarter}")

    # Backlog Flow
    for product in products:
        for quarter in quarters:
            if quarter == 1:
                model.addConstr(Bk[product, quarter] == 0, name=f"backlog_{product}_{quarter}")
            else:
                model.addConstr(Bk[product, quarter] == gp.quicksum(late_penalty_per_unit_per_quarter[product] * Bk[product, q] for q in quarters[:quarter]) + \
                                  gp.quicksum(storage_cost_per_unit_per_quarter * x[product, q] for q in quarters[:quarter]), name=f"backlog_{product}_{quarter}")

    variables = {
        "x_I_1": x["I", 1],
        "x_I_2": x["I", 2],
        "x_I_3": x["I", 3],
        "x_I_4": x["I", 4],
        "x_II_1": x["II", 1],
        "x_II_2": x["II", 2],
        "x_II_3": x["II", 3],
        "x_II_4": x["II", 4],
        "x_III_1": x["III", 1],
        "x_III_2": x["III", 2],
        "x_III_3": x["III", 3],
        "x_III_4": x["III", 4],
        "Iv_I_1": Iv["I", 1],
        "Iv_I_2": Iv["I", 2],
        "Iv_I_3": Iv["I", 3],
        "Iv_I_4": Iv["I", 4],
        "Iv_II_1": Iv["II", 1],
        "Iv_II_2": Iv["II", 2],
        "Iv_II_3": Iv["II", 3],
        "Iv_II_4": Iv["II", 4],
        "Iv_III_1": Iv["III", 1],
        "Iv_III_2": Iv["III", 2],
        "Iv_III_3": Iv["III", 3],
        "Iv_III_4": Iv["III", 4],
        "Bk_I_1": Bk["I", 1],
        "Bk_I_2": Bk["I", 2],
        "Bk_I_3": Bk["I", 3],
        "Bk_I_4": Bk["I", 4],
        "Bk_II_1": Bk["II", 1],
        "Bk_II_2": Bk["II", 2],
        "Bk_II_3": Bk["II", 3],
        "Bk_II_4": Bk["II", 4],
        "Bk_III_1": Bk["III", 1],
        "Bk_III_2": Bk["III", 2],
        "Bk_III_3": Bk["III", 3],
        "Bk_III_4": Bk["III", 4]
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "x_I_1": float(variables["x_I_1"].X),
        "x_I_2": float(variables["x_I_2"].X),
        "x_I_3": float(variables["x_I_3"].X),
        "x_I_4": float(variables["x_I_4"].X),
        "x_II_1": float(variables["x_II_1"].X),
        "x_II_2": float(variables["x_II_2"].X),
        "x_II_3": float(variables["x_II_3"].X),
        "x_II_4": float(variables["x_II_4"].X),
        "x_III_1": float(variables["x_III_1"].X),
        "x_III_2": float(variables["x_III_2"].X),
        "x_III_3": float(variables["x_III_3"].X),
        "x_III_4": float(variables["x_III_4"].X),
        "Iv_I_1": float(variables["Iv_I_1"].X),
        "Iv_I_2": float(variables["Iv_I_2"].X),
        "Iv_I_3": float(variables["Iv_I_3"].X),
        "Iv_I_4": float(variables["Iv_I_4"].X),
        "Iv_II_1": float(variables["Iv_II_1"].X),
        "Iv_II_2": float(variables["Iv_II_2"].X),
        "Iv_II_3": float(variables["Iv_II_3"].X),
        "Iv_II_4": float(variables["Iv_II_4"].X),
        "Iv_III_1": float(variables["Iv_III_1"].X),
        "Iv_III_2": float(variables["Iv_III_2"].X),
        "Iv_III_3": float(variables["Iv_III_3"].X),
        "Iv_III_4": float(variables["Iv_III_4"].X),
        "Bk_I_1": float(variables["Bk_I_1"].X),
        "Bk_I_2": float(variables["Bk_I_2"].X),
        "Bk_I_3": float(variables["Bk_I_3"].X),
        "Bk_I_4": float(variables["Bk_I_4"].X),
        "Bk_II_1": float(variables["Bk_II_1"].X),
        "Bk_II_2": float(variables["Bk_II_2"].X),
        "Bk_II_3": float(variables["Bk_II_3"].X),
        "Bk_II_4": float(variables["Bk_II_4"].X),
        "Bk_III_1": float(variables["Bk_III_1"].X),
        "Bk_III_2": float(variables["Bk_III_2"].X),
        "Bk_III_3": float(variables["Bk_III_3"].X),
        "Bk_III_4": float(variables["Bk_III_4"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }