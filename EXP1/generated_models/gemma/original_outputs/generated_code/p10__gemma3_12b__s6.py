import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Create decision variables
    shirts = model.addVar(vtype=GRB.CONTINUOUS, name="shirts")
    shorts = model.addVar(vtype=GRB.CONTINUOUS, name="shorts")
    pants = model.addVar(vtype=GRB.CONTINUOUS, name="pants")
    y_shirts = model.addVar(vtype=GRB.BINARY, name="y_shirts")
    y_shorts_m = model.addVar(vtype=GRB.BINARY, name="y_shorts_m")
    y_pants = model.addVar(vtype=GRB.BINARY, name="y_pants")

    # Set the objective function
    model.setObjective(
        shirts * data["unit_contribution"]["shirts"] +
        shorts * data["unit_contribution"]["shorts"] +
        pants * data["unit_contribution"]["pants"] -
        data["rental_cost"]["shirts"] * y_shirts -
        data["rental_cost"]["shorts"] * y_shorts_m -
        data["rental_cost"]["pants"] * y_pants,
        gp.GRB.MAXIMIZE
    )

    # Add constraints
    model.addConstr(
        shirts * data["labor_per_unit"]["shirts"] +
        shorts * data["labor_per_unit"]["shorts"] +
        pants * data["labor_per_unit"]["pants"] <= data["labor_available"],
        "labor_constraint"
    )

    model.addConstr(
        shirts * data["cloth_per_unit"]["shirts"] +
        shorts * data["cloth_per_unit"]["shorts"] +
        pants * data["cloth_per_unit"]["pants"] <= data["cloth_available"],
        "cloth_constraint"
    )

    model.addConstr(
        y_shirts == 1 if shirts > 0 else 0, "shirt_machinery"
    )
    model.addConstr(
        y_shorts_m == 1 if shorts > 0 else 0, "shorts_machinery"
    )
    model.addConstr(
        y_pants == 1 if pants > 0 else 0, "pants_machinery"
    )

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

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "shirts": float(variables["shirts"].X),
        "shorts": float(variables["shorts"].X),
        "pants": float(variables["pants"].X),
        "y_shirts": float(variables["y_shirts"].X),
        "y_shorts_m": float(variables["y_shorts_m"].X),
        "y_pants": float(variables["y_pants"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }