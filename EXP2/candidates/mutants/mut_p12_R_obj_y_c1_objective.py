"""Certified-reference candidate for problem 12.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'y_c1', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_c2', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_c3', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_c4', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y_c5', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'f_c1_s1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c1_s2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c1_s3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c1_s4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c1_s5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c2_s1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c2_s2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c2_s3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c2_s4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c2_s5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c3_s1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c3_s2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c3_s3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c3_s4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c3_s5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c4_s1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c4_s2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c4_s3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c4_s4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c4_s5', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c5_s1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c5_s2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c5_s3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c5_s4', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'f_c5_s5', 'vtype': 'C', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '>=',
  'rhs': 589,
  'terms': [('f_c1_s1', 1), ('f_c2_s1', 1), ('f_c3_s1', 1), ('f_c4_s1', 1), ('f_c5_s1', 1)]},
 {'name': 'constraint_002',
  'sense': '>=',
  'rhs': 962,
  'terms': [('f_c1_s2', 1), ('f_c2_s2', 1), ('f_c3_s2', 1), ('f_c4_s2', 1), ('f_c5_s2', 1)]},
 {'name': 'constraint_003',
  'sense': '>=',
  'rhs': 966,
  'terms': [('f_c1_s3', 1), ('f_c2_s3', 1), ('f_c3_s3', 1), ('f_c4_s3', 1), ('f_c5_s3', 1)]},
 {'name': 'constraint_004',
  'sense': '>=',
  'rhs': 643,
  'terms': [('f_c1_s4', 1), ('f_c2_s4', 1), ('f_c3_s4', 1), ('f_c4_s4', 1), ('f_c5_s4', 1)]},
 {'name': 'constraint_005',
  'sense': '>=',
  'rhs': 904,
  'terms': [('f_c1_s5', 1), ('f_c2_s5', 1), ('f_c3_s5', 1), ('f_c4_s5', 1), ('f_c5_s5', 1)]},
 {'name': 'constraint_006',
  'sense': '<=',
  'rhs': 0,
  'terms': [('f_c1_s1', 1),
            ('f_c1_s2', 1),
            ('f_c1_s3', 1),
            ('f_c1_s4', 1),
            ('f_c1_s5', 1),
            ('y_c1', -1954)]},
 {'name': 'constraint_007', 'sense': '<=', 'rhs': 1, 'terms': [('y_c1', 1)]},
 {'name': 'constraint_008',
  'sense': '<=',
  'rhs': 0,
  'terms': [('f_c2_s1', 1),
            ('f_c2_s2', 1),
            ('f_c2_s3', 1),
            ('f_c2_s4', 1),
            ('f_c2_s5', 1),
            ('y_c2', -1446)]},
 {'name': 'constraint_009', 'sense': '<=', 'rhs': 1, 'terms': [('y_c2', 1)]},
 {'name': 'constraint_010',
  'sense': '<=',
  'rhs': 0,
  'terms': [('f_c3_s1', 1),
            ('f_c3_s2', 1),
            ('f_c3_s3', 1),
            ('f_c3_s4', 1),
            ('f_c3_s5', 1),
            ('y_c3', -820)]},
 {'name': 'constraint_011', 'sense': '<=', 'rhs': 1, 'terms': [('y_c3', 1)]},
 {'name': 'constraint_012',
  'sense': '<=',
  'rhs': 0,
  'terms': [('f_c4_s1', 1),
            ('f_c4_s2', 1),
            ('f_c4_s3', 1),
            ('f_c4_s4', 1),
            ('f_c4_s5', 1),
            ('y_c4', -1640)]},
 {'name': 'constraint_013', 'sense': '<=', 'rhs': 1, 'terms': [('y_c4', 1)]},
 {'name': 'constraint_014',
  'sense': '<=',
  'rhs': 0,
  'terms': [('f_c5_s1', 1),
            ('f_c5_s2', 1),
            ('f_c5_s3', 1),
            ('f_c5_s4', 1),
            ('f_c5_s5', 1),
            ('y_c5', -966)]},
 {'name': 'constraint_015', 'sense': '<=', 'rhs': 1, 'terms': [('y_c5', 1)]}]

OBJECTIVE_TERMS = [('y_c1', 151001.0),
 ('y_c2', 192000),
 ('y_c3', 114000),
 ('y_c4', 171000),
 ('y_c5', 160000),
 ('f_c1_s1', 5),
 ('f_c1_s2', 2),
 ('f_c1_s3', 3),
 ('f_c1_s4', 3),
 ('f_c1_s5', 3),
 ('f_c2_s1', 5),
 ('f_c2_s2', 4),
 ('f_c2_s3', 3),
 ('f_c2_s4', 5),
 ('f_c2_s5', 2),
 ('f_c3_s1', 4),
 ('f_c3_s2', 2),
 ('f_c3_s3', 4),
 ('f_c3_s4', 5),
 ('f_c3_s5', 1),
 ('f_c4_s1', 4),
 ('f_c4_s2', 2),
 ('f_c4_s3', 5),
 ('f_c4_s4', 4),
 ('f_c4_s5', 1),
 ('f_c5_s1', 1),
 ('f_c5_s2', 3),
 ('f_c5_s3', 3),
 ('f_c5_s4', 2),
 ('f_c5_s5', 4)]
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
