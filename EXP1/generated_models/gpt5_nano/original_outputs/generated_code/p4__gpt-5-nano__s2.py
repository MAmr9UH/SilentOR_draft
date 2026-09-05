from gurobipy import Model, GRB, quicksum

def build_model(data: dict):
    """
    Build the Gurobi model for the daily nutrition optimization problem.
    Returns the model and a dictionary of variables with keys:
    {
      "chicken": Var,
      "rice": Var,
      "broccoli": Var,
      "tofu": Var,
      "beans": Var
    }
    """
    FOODS = ["chicken", "rice", "broccoli", "tofu", "beans"]

    model = Model()
    model.setParam("OutputFlag", 0)

    # Decision variables: quantity of each food
    variables = {}
    for f in FOODS:
        variables[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f)

    model.update()

    # Nutritional constraints
    model.addConstr(
        quicksum(data["protein"][f] * variables[f] for f in FOODS) >= data["min"]["protein"],
        name="protein_min"
    )
    model.addConstr(
        quicksum(data["carb"][f] * variables[f] for f in FOODS) >= data["min"]["carb"],
        name="carb_min"
    )
    model.addConstr(
        quicksum(data["calories"][f] * variables[f] for f in FOODS) >= data["min"]["calories"],
        name="cal_min"
    )

    # Objective: minimize total cost
    model.setObjective(
        quicksum(data["cost"][f] * variables[f] for f in FOODS),
        GRB.MINIMIZE
    )

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    solution = {
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X),
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }