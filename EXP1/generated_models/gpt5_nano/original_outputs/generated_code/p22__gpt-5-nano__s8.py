import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_node = data["required_service_node"]
    bandwidth = data["bandwidth"]
    big_m = data.get("big_m", 100)

    # Collect directed edges with positive bandwidth
    edges = []
    max_bw = 0
    for u in nodes:
        bw_row = bandwidth.get(u, {})
        for v in nodes:
            w = bw_row.get(v, 0)
            if w > 0:
                edges.append((u, v, w))
                if w > max_bw:
                    max_bw = w

    # Decision variables
    x_vars = {}
    for (u, v, w) in edges:
        key = f"x_{u}_{v}"
        x_vars[key] = model.addVar(vtype=gp.GRB.BINARY, name=key)

    z = model.addVar(vtype=gp.GRB.CONTINUOUS, name="z", lb=0.0, ub=max(max_bw, big_m))

    # Build in/out incidence lists
    in_dict = {n: [] for n in nodes}
    out_dict = {n: [] for n in nodes}
    for (u, v, w) in edges:
        key = f"x_{u}_{v}"
        xv = x_vars[key]
        out_dict[u].append(xv)
        in_dict[v].append(xv)

    # Flow conservation constraints
    for n in nodes:
        if n == source:
            model.addConstr(gp.quicksum(out_dict[n]) - gp.quicksum(in_dict[n]) == 1)
        elif n == sink:
            model.addConstr(gp.quicksum(in_dict[n]) - gp.quicksum(out_dict[n]) == 1)
        else:
            model.addConstr(gp.quicksum(in_dict[n]) - gp.quicksum(out_dict[n]) == 0)

    # Enforce that the path passes through the required service node
    model.addConstr(gp.quicksum(in_dict[required_node]) == 1)
    model.addConstr(gp.quicksum(out_dict[required_node]) == 1)

    # Bottleneck constraints: z <= w + bigM*(1 - x_e) for all edges e
    for (u, v, w) in edges:
        key = f"x_{u}_{v}"
        model.addConstr(z <= w + big_m * (1 - x_vars[key]))

    model.setObjective(z, gp.GRB.MAXIMIZE)

    # Return model and the flat variables dict as required
    variables = {"z": z}
    for key, var in x_vars.items():
        variables[key] = var

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    obj_val = float(model.ObjVal) if model.Status == gp.GRB.OPTIMAL else float('nan')

    # Build solution dictionary with exact keys
    solution = {}
    keys = [
        "z",
        "x_A_B","x_A_C","x_A_E",
        "x_B_A","x_B_C","x_B_D","x_B_E",
        "x_C_A","x_C_D","x_C_E",
        "x_D_A","x_D_B","x_D_C","x_D_E",
        "x_E_B","x_E_D"
    ]
    for k in keys:
        v = variables[k].X if k in variables else None
        solution[k] = float(v) if v is not None else float('nan')

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }