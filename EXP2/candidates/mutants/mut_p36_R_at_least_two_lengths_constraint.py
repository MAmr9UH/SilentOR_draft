"""Certified-reference candidate for problem 36.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'x_1_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_3', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_4', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_3', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'y_1', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_2', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_3', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_4', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '==',
  'rhs': 15,
  'terms': [('x_1_1', 1), ('x_1_2', 1), ('x_1_3', 1), ('x_1_4', 1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 10,
  'terms': [('x_1_2', 1), ('x_1_3', 1), ('x_1_4', 1), ('x_2_1', 1), ('x_2_2', 1), ('x_2_3', 1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 20,
  'terms': [('x_1_3', 1), ('x_1_4', 1), ('x_2_2', 1), ('x_2_3', 1), ('x_3_1', 1), ('x_3_2', 1)]},
 {'name': 'constraint_004',
  'sense': '==',
  'rhs': 12,
  'terms': [('x_1_4', 1), ('x_2_3', 1), ('x_3_2', 1), ('x_4_1', 1)]},
 {'name': 'constraint_005',
  'sense': '<=',
  'rhs': 0,
  'terms': [('x_1_1', 1), ('x_2_1', 1), ('x_3_1', 1), ('x_4_1', 1), ('y_1', -57)]},
 {'name': 'constraint_006',
  'sense': '>=',
  'rhs': 0,
  'terms': [('x_1_1', 1), ('x_2_1', 1), ('x_3_1', 1), ('x_4_1', 1), ('y_1', -1)]},
 {'name': 'constraint_007',
  'sense': '<=',
  'rhs': 0,
  'terms': [('x_1_2', 1), ('x_2_2', 1), ('x_3_2', 1), ('y_2', -57)]},
 {'name': 'constraint_008',
  'sense': '>=',
  'rhs': 0,
  'terms': [('x_1_2', 1), ('x_2_2', 1), ('x_3_2', 1), ('y_2', -1)]},
 {'name': 'constraint_009',
  'sense': '<=',
  'rhs': 0,
  'terms': [('x_1_3', 1), ('x_2_3', 1), ('y_3', -57)]},
 {'name': 'constraint_010',
  'sense': '>=',
  'rhs': 0,
  'terms': [('x_1_3', 1), ('x_2_3', 1), ('y_3', -1)]},
 {'name': 'constraint_011', 'sense': '<=', 'rhs': 0, 'terms': [('x_1_4', 1), ('y_4', -57)]},
 {'name': 'constraint_012', 'sense': '>=', 'rhs': 0, 'terms': [('x_1_4', 1), ('y_4', -1)]},
 {'name': 'constraint_013', 'sense': '<=', 'rhs': 1, 'terms': [('y_1', 1)]},
 {'name': 'constraint_014', 'sense': '<=', 'rhs': 1, 'terms': [('y_2', 1)]},
 {'name': 'constraint_015', 'sense': '<=', 'rhs': 1, 'terms': [('y_3', 1)]},
 {'name': 'constraint_016', 'sense': '<=', 'rhs': 1, 'terms': [('y_4', 1)]},
 {'name': 'constraint_017',
  'sense': '>=',
  'rhs': 1.0,
  'terms': [('y_1', 1), ('y_2', 1), ('y_3', 1), ('y_4', 1)]},
 {'name': 'constraint_018',
  'sense': '<=',
  'rhs': 3,
  'terms': [('y_1', 1), ('y_2', 1), ('y_3', 1), ('y_4', 1)]},
 {'name': 'constraint_019', 'sense': '<=', 'rhs': 1, 'terms': [('y_1', 1), ('y_4', 1)]}]

OBJECTIVE_TERMS = [('x_1_1', 4000),
 ('x_1_2', 7500),
 ('x_1_3', 10500),
 ('x_1_4', 13000),
 ('x_2_1', 4000),
 ('x_2_2', 7500),
 ('x_2_3', 10500),
 ('x_3_1', 4000),
 ('x_3_2', 7500),
 ('x_4_1', 4000)]
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
