import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_service_node = data["required_service_node"]
    bandwidth = data["bandwidth"]
    big_m = data["big_m"]

    # Decision variables
    x = {}
    for i in nodes:
        for j in nodes:
            if bandwidth[i][j] > 0:
                x[i, j] = model.addVar(vtype=GRB.BINARY, name=f"x_{i}_{j}")

    z = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name="z")

    # Objective function
    model.setObjective(z, GRB.MAXIMIZE)

    # Constraints
    # Bottleneck constraint
    for i in nodes:
        for j in nodes:
            if bandwidth[i][j] > 0:
                model.addConstr(bandwidth[i][j] * x[i, j] <= z, name=f"bottleneck_{i}_{j}")

    # Flow conservation constraints
    for node in nodes:
        if node != source and node != sink:
            inflow = gp.quicksum([bandwidth[i, node] * x[i, node] for i in nodes if bandwidth[i,node] > 0])
            outflow = gp.quicksum([bandwidth[node, j] * x[node, j] for j in nodes if bandwidth[node,j] > 0])
            model.addConstr(inflow == outflow, name=f"flow_conservation_{node}")

    # Source constraint
    outflow_source = gp.quicksum([bandwidth[source, j] * x[source, j] for j in nodes if bandwidth[source,j] > 0])
    model.addConstr(outflow_source >= 0, name=f"flow_conservation_{source}")

    # Sink constraint
    inflow_sink = gp.quicksum([bandwidth[i, sink] * x[i, sink] for i in nodes if bandwidth[i,sink] > 0])
    model.addConstr(inflow_sink >= 0, name=f"flow_conservation_{sink}")

    # Path constraints through required service node
    if source != required_service_node and required_service_node != sink:
        model.addConstr(x[source, required_service_node] == 1, name=f"path_through_{source}_{required_service_node}")
        model.addConstr(x[required_service_node, sink] == 1, name=f"path_through_{required_service_node}_{sink}")

    # No loops constraint (simplified - assumes no loops are possible)
    # This is a placeholder and might need more sophisticated handling depending on the problem.


    variables = {
        "z": z,
        "x_A_B": x[("A", "B")],
        "x_A_C": x[("A", "C")],
        "x_A_E": x[("A", "E")],
        "x_B_A": x[("B", "A")],
        "x_B_C": x[("B", "C")],
        "x_B_D": x[("B", "D")],
        "x_B_E": x[("B", "E")],
        "x_C_A": x[("C", "A")],
        "x_C_D": x[("C", "D")],
        "x_C_E": x[("C", "E")],
        "x_D_A": x[("D", "A")],
        "x_D_B": x[("D", "B")],
        "x_D_C": x[("D", "C")],
        "x_D_E": x[("D", "E")],
        "x_E_B": x[("E", "B")],
        "x_E_D": x[("E", "D")]
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
        "z": float(model.ObjVal),
        "x_A_B": float(variables["x_A_B"].X),
        "x_A_C": float(variables["x_A_C"].X),
        "x_A_E": float(variables["x_A_E"].X),
        "x_B_A": float(variables["x_B_A"].X),
        "x_B_C": float(variables["x_B_C"].X),
        "x_B_D": float(variables["x_B_D"].X),
        "x_B_E": float(variables["x_B_E"].X),
        "x_C_A": float(variables["x_C_A"].X),
        "x_C_D": float(variables["x_C_D"].X),
        "x_C_E": float(variables["x_C_E"].X),
        "x_D_A": float(variables["x_D_A"].X),
        "x_D_B": float(variables["x_D_B"].X),
        "x_D_C": float(variables["x_D_C"].X),
        "x_D_E": float(variables["x_D_E"].X),
        "x_E_B": float(variables["x_E_B"].X),
        "x_E_D": float(variables["x_E_D"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }