import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    """
    Build the Gurobi model for selecting exactly one spare-count combination (a,b,c).
    Returns the model and a dictionary of all decision variables with keys:
    w_a_b_c corresponding to each combination.
    """
    model = gp.Model()
    # Silence solver output
    try:
        model.setParam('OutputFlag', 0)
    except Exception:
        pass

    spare_levels = data["spare_levels"]
    N = len(spare_levels)

    # reliabilities
    rel1 = data["reliability"]["1"]
    rel2 = data["reliability"]["2"]
    rel3 = data["reliability"]["3"]

    # unit prices and weights
    P1 = data["unit_price"]["1"]
    P2 = data["unit_price"]["2"]
    P3 = data["unit_price"]["3"]

    W1 = data["unit_weight"]["1"]
    W2 = data["unit_weight"]["2"]
    W3 = data["unit_weight"]["3"]

    # Decision variables: w_a_b_c
    w = {}
    for a in range(N):
        for b in range(N):
            for c in range(N):
                key = f"w_{a}_{b}_{c}"
                w[key] = model.addVar(vtype=GRB.BINARY, name=key)

    model.update()

    # Exactly one combination is selected
    model.addConstr(quicksum(w[f"w_{a}_{b}_{c}"] for a in range(N) for b in range(N) for c in range(N)) == 1, name="OneCombo")

    # Budget constraint: sum w*(a*P1 + b*P2 + c*P3) <= budget
    budget = data["budget"]
    model.addConstr(
        quicksum(w[f"w_{a}_{b}_{c}"] * (a * P1 + b * P2 + c * P3) for a in range(N) for b in range(N) for c in range(N)) <= budget,
        name="Budget"
    )

    # Weight constraint: sum w*(a*W1 + b*W2 + c*W3) <= weight_limit
    weight_limit = data["weight_limit"]
    model.addConstr(
        quicksum(w[f"w_{a}_{b}_{c}"] * (a * W1 + b * W2 + c * W3) for a in range(N) for b in range(N) for c in range(N)) <= weight_limit,
        name="Weight"
    )

    # Objective: maximize product of reliabilities
    model.setObjective(
        quicksum(w[f"w_{a}_{b}_{c}"] * (rel1[a] * rel2[b] * rel3[c]) for a in range(N) for b in range(N) for c in range(N)),
        GRB.MAXIMIZE
    )

    # Return model and the flat dict of variables
    return model, w


def solve(data: dict) -> dict:
    """
    Build the model, solve it, and return the solution in the required schema.
    """
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective = float(model.ObjVal) if model.Status == GRB.OPTIMAL else float('nan')

    # Collect solution for all w_a_b_c variables
    solution = {}
    N = len(data["spare_levels"])
    for a in range(N):
        for b in range(N):
            for c in range(N):
                key = f"w_{a}_{b}_{c}"
                solution[key] = int(round(variables[key].X))

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }