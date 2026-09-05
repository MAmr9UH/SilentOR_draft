import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Initialize model
    m = gp.Model()
    m.Params.OutputFlag = 0  # silence solver output

    nodes = data["nodes"]
    bandwidth = data["bandwidth"]
    source = data["source"]
    sink = data["sink"]
    bottleneck_node = data.get("required_service_node", None)
    big_m = data.get("big_m", 100)

    # Define the edge list according to the problem statement (16 directed edges)
    edge_list = [
        ("A", "B"), ("A", "C"), ("A", "E"),
        ("B", "A"), ("B", "C"), ("B", "D"), ("B", "E"),
        ("C", "A"), ("C", "D"), ("C", "E"),
        ("D", "A"), ("D", "B"), ("D", "C"), ("D", "E"),
        ("E", "B"), ("E", "D")
    ]

    # Create variables
    edge_vars = {}  # (u,v) -> Var
    z = m.addVar(vtype=GRB.CONTINUOUS, name="z", lb=0.0)

    for (u, v) in edge_list:
        key = f"x_{u}_{v}"
        # Create binary variable for each directed edge
        x = m.addVar(vtype=GRB.BINARY, name=key)
        edge_vars[(u, v)] = x

        # If bandwidth is zero, fix variable to 0
        Bval = bandwidth[u][v]
        if Bval == 0:
            m.addConstr(x == 0)

    m.update()  # ensure variables are registered

    # Build helper mappings for flow constraints
    out_var = {node: [] for node in nodes}
    in_var = {node: [] for node in nodes}
    for (u, v), x in edge_vars.items():
        out_var[u].append(x)
        in_var[v].append(x)

    # Flow conservation: single unit flow from source to sink
    m.addConstr(gp.quicksum(out_var[source]) - gp.quicksum(in_var[source]) == 1)
    m.addConstr(gp.quicksum(out_var[sink]) - gp.quicksum(in_var[sink]) == -1)

    # Ensure the path passes through the required service node (C by default)
    if bottleneck_node is not None:
        m.addConstr(gp.quicksum(out_var[bottleneck_node]) >= 1)
        m.addConstr(gp.quicksum(in_var[bottleneck_node]) >= 1)

    # Bottleneck constraints: for each edge, if used, z <= bandwidth(u,v)
    for (u, v), x in edge_vars.items():
        Bval = bandwidth[u][v]
        m.addConstr(z <= Bval * x + big_m * (1 - x))

    # Objective: maximize bottleneck z
    m.setObjective(z, GRB.MAXIMIZE)

    # Return model and structured variables as required
    variables = {
        "variables_keys": {
            "z": z,
            "x_A_B": edge_vars[("A", "B")],
            "x_A_C": edge_vars[("A", "C")],
            "x_A_E": edge_vars[("A", "E")],
            "x_B_A": edge_vars[("B", "A")],
            "x_B_C": edge_vars[("B", "C")],
            "x_B_D": edge_vars[("B", "D")],
            "x_B_E": edge_vars[("B", "E")],
            "x_C_A": edge_vars[("C", "A")],
            "x_C_D": edge_vars[("C", "D")],
            "x_C_E": edge_vars[("C", "E")],
            "x_D_A": edge_vars[("D", "A")],
            "x_D_B": edge_vars[("D", "B")],
            "x_D_C": edge_vars[("D", "C")],
            "x_D_E": edge_vars[("D", "E")],
            "x_E_B": edge_vars[("E", "B")],
            "x_E_D": edge_vars[("E", "D")]
        },
        "note": "Use exactly these flat keys. Do not use tuple keys. x_A_C means the directed arc A->C."
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)

    # Optimize
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD"
    }
    status = status_map.get(model.Status, str(model.Status))

    # Ensure values are up to date
    model.update()

    z_val = variables["variables_keys"]["z"].X
    solution_vals = {"z": z_val}
    for key, var in variables["variables_keys"].items():
        if key == "z":
            continue
        solution_vals[key] = var.X

    result = {
        "status": status,
        "objective": float(model.ObjVal) if model.ObjVal is not None else None,
        "solution": solution_vals
    }

    return result