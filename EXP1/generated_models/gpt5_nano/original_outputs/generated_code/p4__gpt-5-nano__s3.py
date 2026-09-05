import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Create decision variables (continuous, >= 0)
    var_map = {}
    for food in data["foods"]:
        var_map[food] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=food)
    model.update()

    # Objective: minimize total cost
    cost_expr = gp.quicksum(data["cost"][food] * var_map[food] for food in data["foods"])
    model.setObjective(cost_expr, GRB.MINIMIZE)

    # Nutritional constraints (at least targets)
    protein_expr = gp.quicksum(data["protein"][food] * var_map[food] for food in data["foods"])
    carb_expr = gp.quicksum(data["carb"][food] * var_map[food] for food in data["foods"])
    cal_expr = gp.quicksum(data["calories"][food] * var_map[food] for food in data["foods"])

    model.addConstr(protein_expr >= data["min"]["protein"], name="protein_min")
    model.addConstr(carb_expr >= data["min"]["carb"], name="carb_min")
    model.addConstr(cal_expr >= data["min"]["calories"], name="cal_min")

    model.update()

    # Export flat variables under exact keys
    variables = {
        "chicken": var_map["chicken"],
        "rice": var_map["rice"],
        "broccoli": var_map["broccoli"],
        "tofu": var_map["tofu"],
        "beans": var_map["beans"],
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status as human-readable string
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.CUTOFF: "CUTOFF"
    }
    status_str = status_map.get(status_code, str(status_code))

    objective = float(model.ObjVal)

    solution = {k: float(variables[k].X) for k in ["chicken", "rice", "broccoli", "tofu", "beans"]}

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }