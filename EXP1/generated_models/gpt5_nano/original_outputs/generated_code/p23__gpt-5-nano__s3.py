import math
import gurobipy as gp


def build_model(data: dict) -> tuple:
    # Extract data
    price1 = data["unit_price"]["1"]
    price2 = data["unit_price"]["2"]
    price3 = data["unit_price"]["3"]

    wt1 = data["unit_weight"]["1"]
    wt2 = data["unit_weight"]["2"]
    wt3 = data["unit_weight"]["3"]

    budget = data["budget"]
    weight_limit = data["weight_limit"]

    rel1 = data["reliability"]["1"]  # list of length 6
    rel2 = data["reliability"]["2"]
    rel3 = data["reliability"]["3"]

    log1 = [math.log(v) for v in rel1]
    log2 = [math.log(v) for v in rel2]
    log3 = [math.log(v) for v in rel3]

    model = gp.Model()

    # Decision variables w[a][b][c] for a,b,c in 0..5
    w = [[[None for _ in range(6)] for _ in range(6)] for _ in range(6)]
    variables = {}

    for a in range(6):
        for b in range(6):
            for c in range(6):
                v = model.addVar(vtype=gp.GRB.BINARY, name=f"w_{a}_{b}_{c}")
                w[a][b][c] = v
                variables[f"w_{a}_{b}_{c}"] = v

    model.update()

    # Exactly one combination selected
    model.addConstr(
        gp.quicksum(w[a][b][c] for a in range(6) for b in range(6) for c in range(6)) == 1,
        name="one_combination"
    )

    # Budget constraint
    cost_expr = gp.quicksum(
        (a * price1 + b * price2 + c * price3) * w[a][b][c]
        for a in range(6) for b in range(6) for c in range(6)
    )
    model.addConstr(cost_expr <= budget, name="budget")

    # Weight constraint
    weight_expr = gp.quicksum(
        (a * wt1 + b * wt2 + c * wt3) * w[a][b][c]
        for a in range(6) for b in range(6) for c in range(6)
    )
    model.addConstr(weight_expr <= weight_limit, name="weight")

    # Objective: maximize log(reliability product)
    obj_expr = gp.quicksum(
        (log1[a] + log2[b] + log3[c]) * w[a][b][c]
        for a in range(6) for b in range(6) for c in range(6)
    )
    model.ModelSense = gp.GRB.MAXIMIZE
    model.setObjective(obj_expr)

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    objective_value = float(model.ObjVal)

    solution = {}
    for a in range(6):
        for b in range(6):
            for c in range(6):
                key = f"w_{a}_{b}_{c}"
                solution[key] = float(variables[key].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }