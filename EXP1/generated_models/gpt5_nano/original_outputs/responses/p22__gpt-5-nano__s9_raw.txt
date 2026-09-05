import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    nodes = data.get("nodes", [])
    bandwidth = data.get("bandwidth", {})
    big_m = data.get("big_m", 100)

    # Decision variable: bottleneck bandwidth
    z = model.addVar(vtype=GRB.CONTINUOUS, lb=0.0, name="z")

    # Arc variables: x_from_to for positive-bandwidth arcs
    arc_vars = {}
    arc_bandwidths = {}

    for i in nodes:
        for j in nodes:
            if i == j:
                continue
            b = bandwidth.get(i, {}).get(j, 0)
            if b > 0:
                key = f"x_{i}_{j}"
                var = model.addVar(vtype=GRB.BINARY, name=key)
                arc_vars[key] = var
                arc_bandwidths[key] = b

    # Flow balance constraints for a single path from A to E
    # A is source, E is sink
    # sum_out(A) - sum_in(A) = 1
    sum_out_A = arc_vars["x_A_B"] + arc_vars["x_A_C"] + arc_vars["x_A_E"]
    sum_in_A  = arc_vars["x_B_A"] + arc_vars["x_C_A"] + arc_vars["x_D_A"]
    model.addConstr(sum_out_A - sum_in_A == 1)

    # sum_out(E) - sum_in(E) = -1  (i.e., sum_in(E) - sum_out(E) = 1)
    sum_out_E = arc_vars["x_E_B"] + arc_vars["x_E_D"]
    sum_in_E  = arc_vars["x_A_E"] + arc_vars["x_B_E"] + arc_vars["x_C_E"] + arc_vars["x_D_E"]
    model.addConstr(sum_out_E - sum_in_E == -1)

    # Balance for intermediate nodes B, C, D
    sum_out_B = arc_vars["x_B_A"] + arc_vars["x_B_C"] + arc_vars["x_B_D"] + arc_vars["x_B_E"]
    sum_in_B  = arc_vars["x_A_B"] + arc_vars["x_D_B"] + arc_vars["x_E_B"]
    model.addConstr(sum_out_B - sum_in_B == 0)

    sum_out_C = arc_vars["x_C_A"] + arc_vars["x_C_D"] + arc_vars["x_C_E"]
    sum_in_C  = arc_vars["x_A_C"] + arc_vars["x_B_C"] + arc_vars["x_D_C"]
    model.addConstr(sum_out_C - sum_in_C == 0)

    sum_out_D = arc_vars["x_D_A"] + arc_vars["x_D_B"] + arc_vars["x_D_C"] + arc_vars["x_D_E"]
    sum_in_D  = arc_vars["x_B_D"] + arc_vars["x_C_D"] + arc_vars["x_E_D"]
    model.addConstr(sum_out_D - sum_in_D == 0)

    # Must pass through service node C: exactly one incoming to C and exactly one outgoing from C
    model.addConstr(arc_vars["x_A_C"] + arc_vars["x_B_C"] + arc_vars["x_D_C"] == 1)
    model.addConstr(arc_vars["x_C_A"] + arc_vars["x_C_D"] + arc_vars["x_C_E"] == 1)

    # Degree restrictions to avoid loops
    model.addConstr(sum_out_A <= 1)
    model.addConstr(sum_in_A <= 1)

    model.addConstr(sum_out_B <= 1)
    model.addConstr(sum_in_B <= 1)

    model.addConstr(sum_out_C <= 1)
    model.addConstr(sum_in_C <= 1)

    model.addConstr(sum_out_D <= 1)
    model.addConstr(sum_in_D <= 1)

    model.addConstr(sum_out_E <= 1)
    model.addConstr(sum_in_E <= 1)

    # Link z with arc bandwidths: z <= b when arc is used; otherwise non-binding
    for key, b in arc_bandwidths.items():
        model.addConstr(z <= b + big_m * (1 - arc_vars[key]))

    # Objective: maximize bottleneck z
    model.setObjective(z, GRB.MAXIMIZE)

    model.update()

    # Prepare return dictionary of variables with exact keys
    variables = {"z": z}
    for key, v in arc_vars.items():
        variables[key] = v

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    # Read status and objective
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(status_code, str(status_code))
    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values
    z_val = float(variables["z"].X) if hasattr(variables["z"], "X") else None

    solution = {
        "z": z_val,
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
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }