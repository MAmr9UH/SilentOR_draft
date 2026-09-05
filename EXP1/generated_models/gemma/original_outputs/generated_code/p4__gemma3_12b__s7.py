import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # TODO: create ALL decision variables using numeric values from data
    chicken = model.addVar(vtype=GRB.CONTINUOUS, name="chicken")
    rice = model.addVar(vtype=GRB.CONTINUOUS, name="rice")
    broccoli = model.addVar(vtype=GRB.CONTINUOUS, name="broccoli")
    tofu = model.addVar(vtype=GRB.CONTINUOUS, name="tofu")
    beans = model.addVar(vtype=GRB.CONTINUOUS, name="beans")

    # TODO: set the objective using numeric values from data
    model.setObjective(
        data["cost"]["chicken"] * chicken +
        data["cost"]["rice"] * rice +
        data["cost"]["broccoli"] * broccoli +
        data["cost"]["tofu"] * tofu +
        data["cost"]["beans"] * beans,
        GRB.MINIMIZE
    )

    # TODO: add ALL constraints using numeric values from data
    model.addConstr(
        data["protein"]["chicken"] * chicken +
        data["protein"]["rice"] * rice +
        data["protein"]["broccoli"] * broccoli +
        data["protein"]["tofu"] * tofu +
        data["protein"]["beans"] * beans >= data["min"]["protein"],
        "protein_constraint"
    )

    model.addConstr(
        data["carb"]["chicken"] * chicken +
        data["carb"]["rice"] * rice +
        data["carb"]["broccoli"] * broccoli +
        data["carb"]["tofu"] * tofu +
        data["carb"]["beans"] * beans >= data["min"]["carb"],
        "carb_constraint"
    )

    model.addConstr(
        data["calories"]["chicken"] * chicken +
        data["calories"]["rice"] * rice +
        data["calories"]["broccoli"] * broccoli +
        data["calories"]["tofu"] * tofu +
        data["calories"]["beans"] * beans >= data["min"]["calories"],
        "calorie_constraint"
    )

    variables = {
        "chicken": chicken,
        "rice": rice,
        "broccoli": broccoli,
        "tofu": tofu,
        "beans": beans
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
        "chicken": float(variables["chicken"].X),
        "rice": float(variables["rice"].X),
        "broccoli": float(variables["broccoli"].X),
        "tofu": float(variables["tofu"].X),
        "beans": float(variables["beans"].X)
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }