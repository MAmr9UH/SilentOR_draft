import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    nodes = data["nodes"]
    bandwidth = data["bandwidth"]
    big_m = data.get("big_m", 100)

    # Create arc variables for positive bandwidth edges only
    arc_vars = {}
    max_bw = 0
    for u in nodes:
        for v in nodes:
            if u == v:
                continue
            w = bandwidth[u][v]
            if w > 0:
                key = f"x_{u}_{v}"
                var = model.addVar(vtype=GRB.BINARY, name=key)
                arc_vars[(u, v)] = var
                if w > max_bw:
                    max_bw = w

    # Bottleneck variable
    z = model.addVar(lb=0.0, ub=max_bw if max_bw > 0 else 0.0, vtype=GRB.CONTINUOUS, name="z")

    model.update()

    s = data["source"]
    t = data["sink"]
    C = data["required_service_node"]

    # Flow constraints
    for v in nodes:
        in_vars = [arc_vars[(u, v)] for u in nodes if (u, v) in arc_vars]
        out_vars = [arc_vars[(v, w)] for w in nodes if (v, w) in arc_vars]

        if v == s:
            model.addConstr(gp.quicksum(out_vars) - gp.quicksum(in_vars) == 1)
        elif v == t:
            model.addConstr(gp.quicksum(out_vars) - gp.quicksum(in_vars) == -1)
        elif v == C:
            # Ensure exactly one incoming and one outgoing through C
            model.addConstr(gp.quicksum(in_vars) == 1)
            model.addConstr(gp.quicksum(out_vars) == 1)
        else:
            model.addConstr(gp.quicksum(out_vars) - gp.quicksum(in_vars) == 0)

    # Link bottleneck to used edges
    for (u, v), var in arc_vars.items():
        w = bandwidth[u][v]
        model.addConstr(z <= w + big_m * (1 - var))

    model.setObjective(z, GRB.MAXIMIZE)

    # Build the variables dictionary with exact keys
    variables = {"z": z}
    for (u, v), var in arc_vars.items():
        key = f"x_{u}_{v}"
        variables[key] = var

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
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    z_val = float(variables["z"].X)

    order = ["x_A_B","x_A_C","x_A_E","x_B_A","x_B_C","x_B_D","x_B_E",
             "x_C_A","x_C_D","x_C_E","x_D_A","x_D_B","x_D_C","x_D_E",
             "x_E_B","x_E_D"]
    solution = {"z": z_val}
    for k in order:
        if k in variables:
            solution[k] = float(variables[k].X)
        else:
            solution[k] = 0.0

    result = {
        "status": status_str,
        "objective": z_val,
        "solution": solution
    }
    return result