import gurobipy as gp

def build_model(data: dict):
    model = gp.Model()

    centers = data["centers"]
    stores = data["stores"]

    opening_cost = data["fixed_opening_cost"]
    transport_cost = data["transport_cost"]
    demand = data["demand"]
    capacity = data["capacity"]

    # Decision variables
    y = {}
    for idx, cid in enumerate(centers, start=1):
        y[cid] = model.addVar(vtype=gp.GRB.BINARY, name=f"y_{cid}")

    f = {}
    for cid in centers:
        f[cid] = {}
        for sid in stores:
            f[cid][sid] = model.addVar(vtype=gp.GRB.CONTINUOUS, lb=0.0, name=f"f_{cid}_{sid}")

    model.update()

    # Objective: minimize opening costs + transportation costs
    opening_term = gp.quicksum(opening_cost[cid] * y[cid] for cid in centers)
    transport_term = gp.quicksum(transport_cost[cid][sid] * f[cid][sid]
                                 for cid in centers for sid in stores)
    model.setObjective(opening_term + transport_term, sense=gp.GRB.MINIMIZE)

    # Constraints: meet demand at each store
    for sid in stores:
        model.addConstr(gp.quicksum(f[cid][sid] for cid in centers) == demand[sid],
                        name=f"dem_{sid}")

    # Constraints: capacity of each center and linkage to opening
    for cid in centers:
        model.addConstr(gp.quicksum(f[cid][sid] for sid in stores) <= capacity[cid] * y[cid],
                        name=f"cap_{cid}")

    # Prepare the variables dict to return
    variables = {}

    # y variables: y_c1 ... y_c7
    for i, cid in enumerate(centers, start=1):
        key = f"y_c{i}"
        variables[key] = y[cid]

    # f variables: f_c1_s1 ... f_c7_s9
    for i, cid in enumerate(centers, start=1):
        for j, sid in enumerate(stores, start=1):
            key = f"f_c{i}_s{j}"
            variables[key] = f[cid][sid]

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to readable string
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
        status_str = str(st)

    # Build solution vector
    solution = {}
    for key, var in variables.items():
        solution[key] = var.X

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }