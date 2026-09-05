"""Certified-reference candidate for problem 10.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'shirts', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'shorts', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'pants', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'y_shirts', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_shorts_m', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_pants', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '<=',
  'rhs': 150,
  'terms': [('shirts', 3), ('shorts', 2), ('pants', 6)]},
 {'name': 'constraint_002',
  'sense': '<=',
  'rhs': 160.001,
  'terms': [('shirts', 4), ('shorts', 3), ('pants', 4)]},
 {'name': 'constraint_003', 'sense': '<=', 'rhs': 0, 'terms': [('shirts', 1), ('y_shirts', -1000)]},
 {'name': 'constraint_004',
  'sense': '<=',
  'rhs': 0,
  'terms': [('shorts', 1), ('y_shorts_m', -1000)]},
 {'name': 'constraint_005', 'sense': '<=', 'rhs': 0, 'terms': [('pants', 1), ('y_pants', -1000)]}]

OBJECTIVE_TERMS = [('shirts', 6),
 ('shorts', 4),
 ('pants', 7),
 ('y_shirts', -200),
 ('y_shorts_m', -150),
 ('y_pants', -100)]
OBJECTIVE_SENSE = 'maximize'


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.Params.OutputFlag = 0
    variables = {}
    type_map = {"C": GRB.CONTINUOUS, "I": GRB.INTEGER, "B": GRB.BINARY}
    for spec in VARIABLE_SPECS:
        kwargs = {"vtype": type_map[spec["vtype"]], "name": spec["name"]}
        if spec["lb"] is not None:
            kwargs["lb"] = spec["lb"]
        else:
            kwargs["lb"] = -GRB.INFINITY
        if spec["ub"] is not None:
            kwargs["ub"] = spec["ub"]
        variables[spec["name"]] = model.addVar(**kwargs)

    for spec in CONSTRAINT_SPECS:
        expression = gp.quicksum(coefficient * variables[name]
                                 for name, coefficient in spec["terms"])
        if spec["sense"] == "<=":
            model.addConstr(expression <= spec["rhs"], name=spec["name"])
        elif spec["sense"] == ">=":
            model.addConstr(expression >= spec["rhs"], name=spec["name"])
        else:
            model.addConstr(expression == spec["rhs"], name=spec["name"])

    objective = gp.quicksum(coefficient * variables[name]
                            for name, coefficient in OBJECTIVE_TERMS)
    model.setObjective(objective, GRB.MAXIMIZE if OBJECTIVE_SENSE == "maximize"
                       else GRB.MINIMIZE)
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
    status = status_map.get(model.Status, str(model.Status))
    if model.SolCount <= 0:
        return {"status": status, "objective": 0.0, "solution": {}}
    solution = {name: float(variable.X) for name, variable in variables.items()}
    return {"status": status, "objective": float(model.ObjVal), "solution": solution}
