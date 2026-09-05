import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    nodes = data["nodes"]
    bandwidth = data["bandwidth"]
    source = data["source"]
    sink = data["sink"]
    service_node = data["required_service_node"]
    big_m = data.get("big_m", 100)

    model = gp.Model()

    # Decision variables
    z = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="z")
    x_vars = {}
    for i in nodes:
        for j in nodes:
            w = bandwidth[i][j]
            if w > 0:
                key = f"x_{i}_{j}"
                x = model.addVar(vtype=GRB.BINARY, name=key)
                x_vars[key] = x

    model.update()

    # Flow balance constraints
    for i in nodes:
        # Outgoing edges from i
        out_vars = []
        for j in nodes:
            if bandwidth[i][j] > 0:
                out_vars.append(x_vars[f"x_{i}_{j}"])
        # Incoming edges to i
        in_vars = []
        for k in nodes:
            if bandwidth[k][i] > 0:
                in_vars.append(x_vars[f"x_{k}_{i}"])
        out_expr = gp.quicksum(out_vars) if out_vars else 0
        in_expr = gp.quicksum(in_vars) if in_vars else 0

        if i == source:
            model.addConstr(out_expr - in_expr == 1, name=f"flow_{i}")
        elif i == sink:
            model.addConstr(in_expr - out_expr == 1, name=f"flow_{i}")
        elif i == service_node:
            # Ensure the service node is on the path
            model.addConstr(in_expr == 1, name=f"in_on_{i}")
            model.addConstr(out_expr == 1, name=f"out_on_{i}")
        else:
            model.addConstr(in_expr - out_expr == 0, name=f"flow_{i}")

    # Bottleneck constraints (z <= bandwidth along every used edge)
    for i in nodes:
        for j in nodes:
            if bandwidth[i][j] > 0:
                w = bandwidth[i][j]
                key = f"x_{i}_{j}"
                model.addConstr(z <= w + big_m * (1 - x_vars[key]))

    model.setObjective(z, GRB.MAXIMIZE)

    return model, {"z": z, **x_vars}


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
    }
    status_code = model.Status
    status_str = status_map.get(status_code, str(status_code))

    model.update()
    solution = {}
    solution["z"] = float(variables["z"].X)
    # Include all x variables in a deterministic order
    for key in sorted([k for k in variables.keys() if k != "z"]):
        solution[key] = float(variables[key].X)

    objective = float(model.ObjVal)

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }