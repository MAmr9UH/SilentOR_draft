import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    products = ["I", "II", "III"]
    quarters = [1, 2, 3, 4]

    model = gp.Model()
    model.setParam('OutputFlag', 0)

    capacity = data["capacity_hours_per_quarter"]
    hours_per_unit = data["hours_per_unit"]
    orders = data["orders"]
    storage_cost = data["storage_cost_per_unit_per_quarter"]
    penalties = data["late_penalty_per_unit_per_quarter"]
    end_inventory_target = data.get("required_ending_inventory", 150)

    # Decision variables
    x_vars = {}  # produced in quarter
    Iv_vars = {}  # ending inventory in quarter
    Bk_vars = {}  # backlog (not delivered) at end of quarter

    for P in products:
        for q in quarters:
            x_vars[(P, q)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"x_{P}_{q}")
            Iv_vars[(P, q)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"Iv_{P}_{q}")
            Bk_vars[(P, q)] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"Bk_{P}_{q}")

    model.update()

    # 1) Production capacity per quarter
    for q in quarters:
        model.addConstr(
            quicksum(hours_per_unit[P] * x_vars[(P, q)] for P in products) <= capacity,
            name=f"capacity_q{q}"
        )

    # 2) Quadrant I cannot be produced in quarter 2
    model.addConstr(x_vars[("I", 2)] == 0, name="block_I_q2")

    # 3) Inventory balance equations
    for P in products:
        for q in quarters:
            Dpq = orders[f"{P}_{q}"]
            if q == 1:
                Iv_prev = 0
                model.addConstr(
                    Iv_vars[(P, q)] == x_vars[(P, q)] - Dpq + Bk_vars[(P, q)],
                    name=f"balance_{P}_{q}"
                )
            else:
                model.addConstr(
                    Iv_vars[(P, q)] == Iv_vars[(P, q - 1)] + x_vars[(P, q)] - Dpq + Bk_vars[(P, q)],
                    name=f"balance_{P}_{q}"
                )

    # 4) Ending inventory must meet requirement for quarter 4
    for P in products:
        model.addConstr(Iv_vars[(P, 4)] == end_inventory_target, name=f"endinv_{P}")

    # Objective: minimize storage costs + late penalties
    obj = quicksum(storage_cost * Iv_vars[(P, q)]
                   for P in products for q in quarters) + \
          quicksum(penalties[P] * Bk_vars[(P, q)]
                   for P in products for q in quarters)

    model.setObjective(obj, GRB.MINIMIZE)

    # Prepare the variables dictionary with exact required keys
    variables = {}

    for P in products:
        for q in quarters:
            key = f"x_{P}_{q}"
            variables[key] = x_vars[(P, q)]
    for P in products:
        for q in quarters:
            key = f"Iv_{P}_{q}"
            variables[key] = Iv_vars[(P, q)]
    for P in products:
        for q in quarters:
            key = f"Bk_{P}_{q}"
            variables[key] = Bk_vars[(P, q)]

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_code, str(status_code))

    obj_val = float(model.ObjVal)

    # Build solution dictionary
    solution = {}
    products = ["I", "II", "III"]
    quarters = [1, 2, 3, 4]

    for P in products:
        for q in quarters:
            solution[f"x_{P}_{q}"] = float(variables[f"x_{P}_{q}"].X)

    for P in products:
        for q in quarters:
            solution[f"Iv_{P}_{q}"] = float(variables[f"Iv_{P}_{q}"].X)

    for P in products:
        for q in quarters:
            solution[f"Bk_{P}_{q}"] = float(variables[f"Bk_{P}_{q}"].X)

    result = {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }

    return result