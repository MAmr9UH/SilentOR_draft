import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required = data["required_service_node"]
    bandwidth = data["bandwidth"]
    big_m = data.get("big_m", 100)

    model = gp.Model()
    model.setObjectiveN  # dummy to avoid unused in some environments if needed

    # Variables container with exact required keys
    variables = {}
    # Objective variable
    z = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="z")
    variables["z"] = z

    # Define arcs in the exact key order provided
    arcs_to_consider = [
        ("A", "B"), ("A", "C"), ("A", "E"),
        ("B", "A"), ("B", "C"), ("B", "D"), ("B", "E"),
        ("C", "A"), ("C", "D"), ("C", "E"),
        ("D", "A"), ("D", "B"), ("D", "C"), ("D", "E"),
        ("E", "B"), ("E", "D")
    ]

    # Create binary variables for arcs with positive bandwidth
    arcs_with_capacity = []
    capacities_by_edge = {}
    for (u, v) in arcs_to_consider:
        cap = bandwidth[u][v]
        if cap > 0:
            key = f"x_{u}_{v}"
            var = model.addVar(vtype=GRB.BINARY, name=key)
            variables[key] = var
            arcs_with_capacity.append((u, v))
            capacities_by_edge[(u, v)] = cap

    # Objective: maximize bottleneck z
    model.setObjective(z, GRB.MAXIMIZE)

    # Flow constraints to ensure a single A->E path
    for node in nodes:
        # sum_in to node
        sum_in = gp.quicksum(variables[f"x_{u}_{node}"] for (u, w) in arcs_with_capacity if w == node)
        # sum_out of node
        sum_out = gp.quicksum(variables[f"x_{node}_{w}"] for (u, w) in arcs_with_capacity if u == node)

        if node == source:
            model.addConstr(sum_out - sum_in == 1)
        elif node == sink:
            model.addConstr(sum_in - sum_out == 1)
        else:
            model.addConstr(sum_in - sum_out == 0)

    # Pass through required service node (C) exactly once
    sum_in_C = gp.quicksum(variables[f"x_{u}_C"] for (u, w) in arcs_with_capacity if w == "C")
    sum_out_C = gp.quicksum(variables[f"x_C_{w}"] for (u, w) in arcs_with_capacity if u == "C")
    model.addConstr(sum_in_C == 1)
    model.addConstr(sum_out_C == 1)

    # Bottleneck constraints: z <= capacity of every used arc
    for (u, v) in arcs_with_capacity:
        cap = capacities_by_edge[(u, v)]
        xvar = variables[f"x_{u}_{v}"]
        model.addConstr(z <= cap + big_m * (1 - xvar))

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    # Map status to string
    GRB_STATUS_MAP = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = GRB_STATUS_MAP.get(model.Status, str(model.Status))
    objective = float(model.ObjVal)

    # Build solution dict with required keys
    solution = {
        "z": float(variables["z"].X),
        "x_A_B": float(variables.get("x_A_B").X),
        "x_A_C": float(variables.get("x_A_C").X),
        "x_A_E": float(variables.get("x_A_E").X),
        "x_B_A": float(variables.get("x_B_A").X),
        "x_B_C": float(variables.get("x_B_C").X),
        "x_B_D": float(variables.get("x_B_D").X),
        "x_B_E": float(variables.get("x_B_E").X),
        "x_C_A": float(variables.get("x_C_A").X),
        "x_C_D": float(variables.get("x_C_D").X),
        "x_C_E": float(variables.get("x_C_E").X),
        "x_D_A": float(variables.get("x_D_A").X),
        "x_D_B": float(variables.get("x_D_B").X),
        "x_D_C": float(variables.get("x_D_C").X),
        "x_D_E": float(variables.get("x_D_E").X),
        "x_E_B": float(variables.get("x_E_B").X),
        "x_E_D": float(variables.get("x_E_D").X)
    }

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }