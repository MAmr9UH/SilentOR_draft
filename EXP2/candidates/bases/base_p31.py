"""Certified-reference candidate for problem 31.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'x_1_Donghai_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_Donghai_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_Nanjiang_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_1_Nanjiang_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_Donghai_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_Donghai_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_Nanjiang_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_2_Nanjiang_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_Donghai_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_Donghai_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_Nanjiang_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_3_Nanjiang_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_Donghai_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_Donghai_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_Nanjiang_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_4_Nanjiang_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_Donghai_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_Donghai_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_Nanjiang_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_5_Nanjiang_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_6_Donghai_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_6_Nanjiang_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'p3_shortfall', 'vtype': 'C', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '==',
  'rhs': 1000,
  'terms': [('x_1_Donghai_1', 1), ('x_3_Donghai_1', 1), ('x_4_Donghai_1', 1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 2000,
  'terms': [('x_1_Donghai_2', 1), ('x_2_Donghai_2', 1), ('x_5_Donghai_2', 1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 1500,
  'terms': [('x_2_Donghai_3', 1),
            ('x_3_Donghai_3', 1),
            ('x_4_Donghai_3', 1),
            ('x_5_Donghai_3', 1),
            ('x_6_Donghai_3', 1)]},
 {'name': 'constraint_004',
  'sense': '==',
  'rhs': 2000,
  'terms': [('x_1_Nanjiang_1', 1), ('x_3_Nanjiang_1', 1), ('x_4_Nanjiang_1', 1)]},
 {'name': 'constraint_005',
  'sense': '==',
  'rhs': 1000,
  'terms': [('x_1_Nanjiang_2', 1), ('x_2_Nanjiang_2', 1), ('x_5_Nanjiang_2', 1)]},
 {'name': 'constraint_006',
  'sense': '==',
  'rhs': 1000,
  'terms': [('x_2_Nanjiang_3', 1),
            ('x_3_Nanjiang_3', 1),
            ('x_4_Nanjiang_3', 1),
            ('x_5_Nanjiang_3', 1),
            ('x_6_Nanjiang_3', 1)]},
 {'name': 'constraint_007',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_1_Donghai_1', 1),
            ('x_1_Donghai_2', 1),
            ('x_1_Nanjiang_1', 1),
            ('x_1_Nanjiang_2', 1)]},
 {'name': 'constraint_008',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_2_Donghai_2', 1),
            ('x_2_Donghai_3', 1),
            ('x_2_Nanjiang_2', 1),
            ('x_2_Nanjiang_3', 1)]},
 {'name': 'constraint_009',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_3_Donghai_1', 1),
            ('x_3_Donghai_3', 1),
            ('x_3_Nanjiang_1', 1),
            ('x_3_Nanjiang_3', 1)]},
 {'name': 'constraint_010',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_4_Donghai_1', 1),
            ('x_4_Donghai_3', 1),
            ('x_4_Nanjiang_1', 1),
            ('x_4_Nanjiang_3', 1)]},
 {'name': 'constraint_011',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_5_Donghai_2', 1),
            ('x_5_Donghai_3', 1),
            ('x_5_Nanjiang_2', 1),
            ('x_5_Nanjiang_3', 1)]},
 {'name': 'constraint_012',
  'sense': '<=',
  'rhs': 1500,
  'terms': [('x_6_Donghai_3', 1), ('x_6_Nanjiang_3', 1)]},
 {'name': 'constraint_013',
  'sense': '>=',
  'rhs': 7000,
  'terms': [('x_1_Donghai_1', 1),
            ('x_1_Nanjiang_1', 1),
            ('x_2_Donghai_2', 1),
            ('x_2_Nanjiang_2', 1),
            ('x_3_Donghai_1', 1),
            ('x_3_Nanjiang_1', 1),
            ('x_4_Donghai_3', 1),
            ('x_4_Nanjiang_3', 1),
            ('x_5_Donghai_3', 1),
            ('x_5_Nanjiang_3', 1),
            ('x_6_Donghai_3', 1),
            ('x_6_Nanjiang_3', 1)]},
 {'name': 'constraint_014',
  'sense': '>=',
  'rhs': 8000,
  'terms': [('p3_shortfall', 1),
            ('x_1_Donghai_1', 1),
            ('x_1_Donghai_2', 1),
            ('x_2_Donghai_2', 1),
            ('x_2_Donghai_3', 1),
            ('x_3_Nanjiang_1', 1),
            ('x_3_Nanjiang_3', 1),
            ('x_4_Nanjiang_1', 1),
            ('x_4_Nanjiang_3', 1),
            ('x_5_Donghai_2', 1),
            ('x_5_Donghai_3', 1),
            ('x_6_Nanjiang_3', 1)]}]

OBJECTIVE_TERMS = [('p3_shortfall', 1)]
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
