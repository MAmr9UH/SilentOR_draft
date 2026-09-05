import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    # Decision variables
    shirts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="pants")

    y_shirts = model.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=GRB.BINARY, name="y_pants")

    # Upper bounds for each product when machinery is rented
    M_shirts = min(
        data["labor_available"] // data["labor_per_unit"]["shirts"],
        data["cloth_available"] // data["cloth_per_unit"]["shirts"]
    )
    M_shorts = min(
        data["labor_available"] // data["labor_per_unit"]["shorts"],
        data["cloth_available"] // data["cloth_per_unit"]["shorts"]
    )
    M_pants = min(
        data["labor_available"] // data["labor_per_unit"]["pants"],
        data["cloth_available"] // data["cloth_per_unit"]["pants"]
    )

    model.addConstr(shirts <= M_shirts * y_shirts, name="M_shirts")
    model.addConstr(shorts <= M_shorts * y_shorts_m, name="M_shorts")
    model.addConstr(pants <= M_pants * y_pants, name="M_pants")

    # Resource constraints
    labor_constraint = (
        data["labor_per_unit"]["shirts"] * shirts +
        data["labor_per_unit"]["shorts"] * shorts +
        data["labor_per_unit"]["pants"] * pants
    )
    model.addConstr(labor_constraint <= data["labor_available"], name="Labor")

    cloth_constraint = (
        data["cloth_per_unit"]["shirts"] * shirts +
        data["cloth_per_unit"]["shorts"] * shorts +
        data["cloth_per_unit"]["pants"] * pants
    )
    model.addConstr(cloth_constraint <= data["cloth_available"], name="Cloth")

    # Objective: maximize contribution minus rental
    objective = (
        data["unit_contribution"]["shirts"] * shirts +
        data["unit_contribution"]["shorts"] * shorts +
        data["unit_contribution"]["pants"] * pants -
        data["rental_cost"]["shirts"] * y_shirts -
        data["rental_cost"]["shorts"] * y_shorts_m -
        data["rental_cost"]["pants"] * y_pants
    )
    model.setObjective(objective, GRB.MAXIMIZE)

    variables = {
        "shirts": shirts,
        "shorts": shorts,
        "pants": pants,
        "y_shirts": y_shirts,
        "y_shorts_m": y_shorts_m,
        "y_pants": y_pants
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

    obj_val = float(model.ObjVal)

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "type": "object",
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }