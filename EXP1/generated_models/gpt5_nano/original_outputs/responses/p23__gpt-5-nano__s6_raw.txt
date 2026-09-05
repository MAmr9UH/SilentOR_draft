import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Extract data
    P1 = data["unit_price"]["1"]
    P2 = data["unit_price"]["2"]
    P3 = data["unit_price"]["3"]

    W1 = data["unit_weight"]["1"]
    W2 = data["unit_weight"]["2"]
    W3 = data["unit_weight"]["3"]

    R1 = data["reliability"]["1"]
    R2 = data["reliability"]["2"]
    R3 = data["reliability"]["3"]

    budget = data["budget"]
    weight_limit = data["weight_limit"]

    m = gp.Model()

    # Decision variables: w_i_j_k for i,j,k in {0..5}
    vars_w = {}
    for i in range(6):
        for j in range(6):
            for k in range(6):
                name = f"w_{i}_{j}_{k}"
                vars_w[name] = m.addVar(vtype=GRB.BINARY, name=name)

    m.update()

    # Exactly one combination selected
    m.addConstr(gp.quicksum(vars_w[f"w_{i}_{j}_{k}"]
                          for i in range(6) for j in range(6) for k in range(6)) == 1,
                name="one_combination")

    # Budget and weight constraints
    m.addConstr(gp.quicksum((i * P1 + j * P2 + k * P3) * vars_w[f"w_{i}_{j}_{k}"]
                          for i in range(6) for j in range(6) for k in range(6)) <= budget,
                name="budget")

    m.addConstr(gp.quicksum((i * W1 + j * W2 + k * W3) * vars_w[f"w_{i}_{j}_{k}"]
                          for i in range(6) for j in range(6) for k in range(6)) <= weight_limit,
                name="weight")

    # Objective: maximize the product reliabilities, linearized by using the product as a coefficient
    # Since exactly one combination is chosen, maximize sum w_i_j_k * (R1[i]*R2[j]*R3[k])
    obj = gp.quicksum((R1[i] * R2[j] * R3[k]) * vars_w[f"w_{i}_{j}_{k}"]
                      for i in range(6) for j in range(6) for k in range(6))
    m.setObjective(obj, GRB.MAXIMIZE)

    # Return model and flat dict of variables
    return m, vars_w

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_code)

    objective_val = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {}
    for i in range(6):
        for j in range(6):
            for k in range(6):
                key = f"w_{i}_{j}_{k}"
                solution[key] = float(variables[key].X)

    return {
        "status": status_str,
        "objective": objective_val,
        "solution": solution
    }