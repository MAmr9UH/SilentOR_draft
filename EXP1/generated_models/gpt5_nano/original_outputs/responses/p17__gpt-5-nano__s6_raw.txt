import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Collect variables
    variables = {}

    # y_c1 ... y_c7
    for i in range(1, 8):
        key = f"y_c{i}"
        v = model.addVar(vtype=GRB.BINARY, name=key)
        variables[key] = v

    # f_c{c}_s{s} for c=1..7, s=1..9
    for c in range(1, 8):
        for s in range(1, 10):
            key = f"f_c{c}_s{s}"
            v = model.addVar(vtype=GRB.CONTINUOUS, lb=0, name=key)
            variables[key] = v

    model.update()

    # Demand constraints: sum_c f_c_s == demand_s
    for s in range(1, 10):
        demand = data["demand"][f"s{s}"]
        expr = gp.quicksum(variables[f"f_c{c}_s{s}"] for c in range(1, 8))
        model.addConstr(expr == demand, name=f"Demand_s{s}")

    # Capacity constraints: sum_s f_c_s <= capacity_c * y_c
    for c in range(1, 8):
        cap = data["capacity"][f"c{c}"]
        expr = gp.quicksum(variables[f"f_c{c}_s{s}"] for s in range(1, 10))
        model.addConstr(expr <= cap * variables[f"y_c{c}"], name=f"Cap_c{c}")

    # Objective: minimize opening costs + transportation costs
    opening_cost_expr = gp.quicksum(data["fixed_opening_cost"][f"c{c}"] * variables[f"y_c{c}"] for c in range(1, 8))
    transport_expr = gp.quicksum(
        data["transport_cost"][f"c{c}"][f"s{s}"] * variables[f"f_c{c}_s{s}"]
        for c in range(1, 8) for s in range(1, 10)
    )
    model.setObjective(opening_cost_expr + transport_expr, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(stat, str(stat))
    objective_value = float(model.ObjVal)

    solution = {}
    for i in range(1, 8):
        solution[f"y_c{i}"] = float(variables[f"y_c{i}"].X)
    for c in range(1, 8):
        for s in range(1, 10):
            solution[f"f_c{c}_s{s}"] = float(variables[f"f_c{c}_s{s}"].X)

    return {
        "type": "object",
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }