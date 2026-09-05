import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    model = gp.Model()
    foods = data["foods"]

    # Decision variables: quantity of each food (continuous, >= 0)
    vars = {}
    for f in foods:
        vars[f] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"qty_{f}")

    # Objective: minimize total cost
    model.setObjective(
        quicksum(data["cost"][f] * vars[f] for f in foods),
        GRB.MINIMIZE
    )

    # Nutritional constraints (at least the minimum)
    model.addConstr(
        quicksum(data["protein"][f] * vars[f] for f in foods) >= data["min"]["protein"],
        name="protein_min"
    )
    model.addConstr(
        quicksum(data["carb"][f] * vars[f] for f in foods) >= data["min"]["carb"],
        name="carb_min"
    )
    model.addConstr(
        quicksum(data["calories"][f] * vars[f] for f in foods) >= data["min"]["calories"],
        name="cal_min"
    )

    return model, vars

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to human-readable string
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

    # Read objective and solution
    model.update()
    objective_val = float(model.ObjVal) if model.ObjVal is not None else 0.0
    solution_vals = {}
    for f in data["foods"]:
        solution_vals[f] = float(variables[f].X)

    # Build the required JSON-schema-like structure with actual values
    result = {
        "type": "object",
        "required": ["status", "objective", "solution"],
        "properties": {
            "status": {
                "type": "string"
            },
            "objective": {
                "type": "number",
                "description": "reported objective"
            },
            "solution": {
                "type": "object",
                "required": ["chicken", "rice", "broccoli", "tofu", "beans"],
                "properties": {
                    "chicken": {"type": "number"},
                    "rice": {"type": "number"},
                    "broccoli": {"type": "number"},
                    "tofu": {"type": "number"},
                    "beans": {"type": "number"}
                }
            }
        },
        # Include actual results as part of the object to satisfy the expected data content
        "status": status_str,
        "objective": objective_val,
        "solution": solution_vals
    }

    return result