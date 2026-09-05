"""Certified-reference candidate for problem 42.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'x_1_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_2', 'vtype': 'I', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001', 'sense': '<=', 'rhs': 2, 'terms': [('x_1_1', 1), ('x_1_2', 1)]},
 {'name': 'constraint_002', 'sense': '<=', 'rhs': 3, 'terms': [('x_2_1', 1), ('x_2_2', 1)]},
 {'name': 'constraint_003', 'sense': '<=', 'rhs': 1, 'terms': [('x_3_1', 1), ('x_3_2', 1)]},
 {'name': 'constraint_004',
  'sense': '>=',
  'rhs': 100,
  'terms': [('x_1_1', 50), ('x_2_1', 60), ('x_3_1', 70)]},
 {'name': 'constraint_005',
  'sense': '>=',
  'rhs': 150,
  'terms': [('x_1_2', 70), ('x_2_2', 80), ('x_3_2', 90)]}]

OBJECTIVE_TERMS = [('x_1_1', 100), ('x_1_2', 200), ('x_2_1', 150), ('x_2_2', 250), ('x_3_1', 200), ('x_3_2', 300)]
OBJECTIVE_SENSE = 'minimize'


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
