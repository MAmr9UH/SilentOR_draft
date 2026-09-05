"""Certified-reference candidate for problem 6.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'x_1_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_4', 'vtype': 'C', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '>=',
  'rhs': 185,
  'terms': [('x_2_1', 1),
            ('x_3_1', 1),
            ('x_4_1', 1),
            ('x_5_1', 1),
            ('x_1_2', -1),
            ('x_1_3', -1),
            ('x_1_4', -1),
            ('x_1_5', -1)]},
 {'name': 'constraint_002',
  'sense': '>=',
  'rhs': 15,
  'terms': [('x_1_2', 1),
            ('x_3_2', 1),
            ('x_4_2', 1),
            ('x_5_2', 1),
            ('x_2_1', -1),
            ('x_2_3', -1),
            ('x_2_4', -1),
            ('x_2_5', -1)]},
 {'name': 'constraint_003',
  'sense': '>=',
  'rhs': 390,
  'terms': [('x_1_3', 1),
            ('x_2_3', 1),
            ('x_4_3', 1),
            ('x_5_3', 1),
            ('x_3_1', -1),
            ('x_3_2', -1),
            ('x_3_4', -1),
            ('x_3_5', -1)]},
 {'name': 'constraint_004',
  'sense': '>=',
  'rhs': -280,
  'terms': [('x_1_4', 1),
            ('x_2_4', 1),
            ('x_3_4', 1),
            ('x_5_4', 1),
            ('x_4_1', -1),
            ('x_4_2', -1),
            ('x_4_3', -1),
            ('x_4_5', -1)]},
 {'name': 'constraint_005',
  'sense': '>=',
  'rhs': -310,
  'terms': [('x_1_5', 1),
            ('x_2_5', 1),
            ('x_3_5', 1),
            ('x_4_5', 1),
            ('x_5_1', -1),
            ('x_5_2', -1),
            ('x_5_3', -1),
            ('x_5_4', -1)]}]

OBJECTIVE_TERMS = [('x_1_2', 10),
 ('x_1_3', 12),
 ('x_1_4', 17),
 ('x_1_5', 34),
 ('x_2_1', 10),
 ('x_2_3', 18),
 ('x_2_4', 8),
 ('x_2_5', 46),
 ('x_3_1', 12),
 ('x_3_2', 18),
 ('x_3_4', 9),
 ('x_3_5', 27),
 ('x_4_1', 17),
 ('x_4_2', 8),
 ('x_4_3', 9),
 ('x_4_5', 20),
 ('x_5_1', 34),
 ('x_5_2', 46),
 ('x_5_3', 27),
 ('x_5_4', 20)]
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
