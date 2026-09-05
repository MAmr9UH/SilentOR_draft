import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    # Create model
    model = gp.Model()

    # Helpers
    Pset = ["I", "II", "III"]
    Qset = [1, 2, 3, 4]

    # Parameters from data
    orders = data["orders"]  # dict with keys like "I_1", "II_3", etc.
    hours_per_unit = data["hours_per_unit"]  # dict {"I": 2, "II": 4, "III": 3}
    capacity = data["capacity_hours_per_quarter"]
    initial_inventory = data["initial_inventory"]  # 0
    ending_inventory_required = data["required_ending_inventory"]  # 150
    late_penalty = data["late_penalty_per_unit_per_quarter"]  # {"I":20,"II":20,"III":10}
    storage_cost = data["storage_cost_per_unit_per_quarter"]  # 5
    # I cannot be produced in quarter 2
    blocked_quarter_I = 2

    # Decision variables (to be returned in `variables` dict)
    x = {p: {} for p in Pset}   # production quantities
    Iv = {p: {} for p in Pset}  # ending inventory
    Bk = {p: {} for p in Pset}  # backlog (not delivered by end of quarter)

    y = {p: {} for p in Pset}   # on-time deliveries in quarter (not required to return but used in constraints)

    # Build variables
    for p in Pset:
        for q in Qset:
            var_name = f"x_{p}_{q}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=var_name)
            x[p][q] = v

            var_name = f"Iv_{p}_{q}"
            v = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=var_name)
            Iv[p][q] = v

            var_name = f"Bk_{p}_{q}"
            # backlog cannot exceed the quarter's demand
            Dpq = orders[f"{p}_{q}"]
            v = model.addVar(lb=0.0, ub=Dpq, vtype=GRB.CONTINUOUS, name=var_name)
            Bk[p][q] = v

            # y (on-time deliveries for quarter q)
            var_name = f"y_{p}_{q}"
            v = model.addVar(lb=0.0, ub=Dpq, vtype=GRB.CONTINUOUS, name=var_name)
            y[p][q] = v

    # Add constraints
    # 1) Hours capacity constraint per quarter
    for q in Qset:
        expr = 0
        expr += hours_per_unit["I"] * x["I"][q]
        expr += hours_per_unit["II"] * x["II"][q]
        expr += hours_per_unit["III"] * x["III"][q]
        model.addConstr(expr <= capacity, name=f"Cap_Q{q}")

    # 2) Production blocked in quarter 2 for product I
    model.addConstr(x["I"][2] == 0, name="Block_I_Q2")

    # 3) Balance and relation between inventory, backlog, and deliveries
    # Iv balance: Iv_p_q = Iv_p_(q-1) + x_p_q - y_p_q
    for p in Pset:
        for q in Qset:
            if q == 1:
                model.addConstr(Iv[p][q] == initial_inventory + x[p][q] - y[p][q],
                                name=f"Iv_balance_{p}_{q}")
            else:
                model.addConstr(Iv[p][q] == Iv[p][q-1] + x[p][q] - y[p][q],
                                name=f"Iv_balance_{p}_{q}")

    # 4) On-time delivery constraint: y_p_q <= available supply
    # Implemented as y_p_q <= Iv_p_(q-1) + x_p_q
    for p in Pset:
        for q in Qset:
            if q == 1:
                model.addConstr(y[p][q] <= initial_inventory + x[p][q], name=f"OnTime_cap_{p}_{q}")
            else:
                model.addConstr(y[p][q] <= Iv[p][q-1] + x[p][q], name=f"OnTime_cap_{p}_{q}")

    # 5) Backlog definition: Bk_p_q + y_p_q = D_p_q
    for p in Pset:
        for q in Qset:
            Dpq = orders[f"{p}_{q}"]
            model.addConstr(Bk[p][q] + y[p][q] == Dpq, name=f"Backlog_def_{p}_{q}")

    # 6) Ending inventory requirement at Q=4
    for p in Pset:
        model.addConstr(Iv[p][4] == ending_inventory_required, name=f"EndingInv_{p}")

    # 7) Ending backlog not strictly required to be zero; allow any nonnegative backlog

    # 8) Objective: minimize storage costs + penalties for backlog
    storage_cost_sum = gp.quicksum(storage_cost * Iv[p][q] for p in Pset for q in Qset)
    penalty_sum = gp.quicksum(late_penalty[p] * Bk[p][q] for p in Pset for q in Qset)
    model.setObjective(storage_cost_sum + penalty_sum, GRB.MINIMIZE)

    # Prepare the variables dictionary to return
    variables = {}
    for p in Pset:
        for q in Qset:
            variables[f"x_{p}_{q}"] = x[p][q]
            variables[f"Iv_{p}_{q}"] = Iv[p][q]
            variables[f"Bk_{p}_{q}"] = Bk[p][q]

    # We do not include y in the returned variables per the required schema

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_str = "UNKNOWN"
    st = model.Status
    if st == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = "OTHER"

    obj_val = float(model.ObjVal)

    # Build solution dictionary with required keys
    solution = {}
    for p in ["I", "II", "III"]:
        for q in [1, 2, 3, 4]:
            key = f"x_{p}_{q}"
            solution[key] = float(variables[key].X)

    for p in ["I", "II", "III"]:
        for q in [1, 2, 3, 4]:
            key = f"Iv_{p}_{q}"
            solution[key] = float(variables[key].X)

    for p in ["I", "II", "III"]:
        for q in [1, 2, 3, 4]:
            key = f"Bk_{p}_{q}"
            solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }