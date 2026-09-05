import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Data extraction
    # Orders D[p][q]
    prod_list = ["I", "II", "III"]
    quarter_list = [1, 2, 3, 4]

    D = {p: {q: 0 for q in quarter_list} for p in prod_list}
    for q in quarter_list:
        D["I"][q] = int(data["orders"][f"I_{q}"])
        D["II"][q] = int(data["orders"][f"II_{q}"])
        D["III"][q] = int(data["orders"][f"III_{q}"])

    hours_per_unit = data["hours_per_unit"]
    capacity = data["capacity_hours_per_quarter"]

    # Penalties and costs
    lp = data["late_penalty_per_unit_per_quarter"]
    storage_cost = data["storage_cost_per_unit_per_quarter"]

    # Decision variables
    # x_p_q: production
    x = {p: {q: None for q in quarter_list} for p in prod_list}
    # Iv_p_q: ending inventory
    Iv = {p: {q: None for q in quarter_list} for p in prod_list}
    # Bk_p_q: backlog at end of quarter
    Bk = {p: {q: None for q in quarter_list} for p in prod_list}

    # Create variables
    for p in prod_list:
        for q in quarter_list:
            x[p][q] = model.addVar(lb=0.0, name=f"x_{p}_{q}")
            Iv[p][q] = model.addVar(lb=0.0, name=f"Iv_{p}_{q}")
            Bk[p][q] = model.addVar(lb=0.0, name=f"Bk_{p}_{q}")

    # Objective: minimize storage costs plus late penalties
    storage_term = gp.quicksum(storage_cost * Iv[p][q] for p in prod_list for q in quarter_list)
    penalty_term = gp.quicksum(lp[p] * Bk[p][q] for p in prod_list for q in quarter_list)
    model.setObjective(storage_term + penalty_term, GRB.MINIMIZE)

    # Constraints

    # 1) Capacity constraints per quarter
    for q in quarter_list:
        model.addConstr(2 * x["I"][q] + 4 * x["II"][q] + 3 * x["III"][q] <= capacity,
                        name=f"cap_q{q}")

    # 2) Product I cannot be produced in quarter 2
    model.addConstr(x["I"][2] == 0, name="prod_I_q2_block")

    # 3) Balance/inventory-backlog evolution
    # Iv_p_q = Iv_p_(q-1) + x_p_q - D_p_q + Bk_p_q - Bk_p_(q-1)
    for p in prod_list:
        for q in quarter_list:
            if q == 1:
                # Iv_p_1 = Iv_p_0 + x_p_1 - D_p_1 + Bk_p_1 - Bk_p_0
                # Iv_p_0 = 0, Bk_p_0 = 0
                model.addConstr(Iv[p][1] == x[p][1] - D[p][1] + Bk[p][1],
                                name=f"bal_Iv_{p}_{q}")
                # Backlog growth constraints for q=1
                model.addConstr(Bk[p][1] <= D[p][1], name=f"bk1_bound_{p}")
                model.addConstr(Bk[p][1] >= D[p][1] - x[p][1], name=f"bk1_minflow_{p}")
            else:
                model.addConstr(Iv[p][q] == Iv[p][q-1] + x[p][q] - D[p][q] + Bk[p][q] - Bk[p][q-1],
                                name=f"bal_Iv_{p}_{q}")
                # Backlog progression bounds
                model.addConstr(Bk[p][q] - Bk[p][q-1] <= D[p][q], name=f"bk_inc_bound_{p}_{q}")
                model.addConstr(Bk[p][q] - Bk[p][q-1] >= D[p][q] - (Iv[p][q-1] + x[p][q]),
                                name=f"bk_growth_{p}_{q}")

    # 4) End inventory constraints: ending inventory at end of quarter 4 must be 150 for each product
    end_inv_target = data["required_ending_inventory"]
    for p in prod_list:
        model.addConstr(Iv[p][4] == end_inv_target, name=f"end_inv_{p}")

    # 5) Initial conditions: Iv_p_0 and Bk_p_0 are implicitly 0 (handled in equations by using literals)

    # Return model and variable mapping
    variables = {}
    for p in prod_list:
        for q in quarter_list:
            variables[f"x_{p}_{q}"] = x[p][q]
    for p in prod_list:
        for q in quarter_list:
            variables[f"Iv_{p}_{q}"] = Iv[p][q]
    for p in prod_list:
        for q in quarter_list:
            variables[f"Bk_{p}_{q}"] = Bk[p][q]

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Prepare status string
    if model.Status == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif model.Status == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif model.Status == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif model.Status == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif model.Status == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(model.Status)

    model.update()
    obj_val = float(model.ObjVal)

    # Build solution dictionary with exact keys and values
    solution = {}
    for key in [
        "x_I_1","x_I_2","x_I_3","x_I_4",
        "x_II_1","x_II_2","x_II_3","x_II_4",
        "x_III_1","x_III_2","x_III_3","x_III_4",
        "Iv_I_1","Iv_I_2","Iv_I_3","Iv_I_4",
        "Iv_II_1","Iv_II_2","Iv_II_3","Iv_II_4",
        "Iv_III_1","Iv_III_2","Iv_III_3","Iv_III_4",
        "Bk_I_1","Bk_I_2","Bk_I_3","Bk_I_4",
        "Bk_II_1","Bk_II_2","Bk_II_3","Bk_II_4",
        "Bk_III_1","Bk_III_2","Bk_III_3","Bk_III_4",
    ]:
        var = variables[key]
        solution[key] = float(var.X)

    return {
        "status": status,
        "objective": obj_val,
        "solution": solution
    }