"""Certified-reference candidate for problem 38.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'prod_I_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_I_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_I_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_I_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_I_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_I_12', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'prod_II_12', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_I_12', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inv_II_12', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'own_storage_12', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_7', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_8', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_9', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_10', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_11', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'external_storage_12', 'vtype': 'C', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '==',
  'rhs': 30000,
  'terms': [('prod_I_7', 1), ('inv_I_7', -1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 30000,
  'terms': [('prod_I_8', 1), ('inv_I_7', 1), ('inv_I_8', -1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 30000,
  'terms': [('prod_I_9', 1), ('inv_I_8', 1), ('inv_I_9', -1)]},
 {'name': 'constraint_004',
  'sense': '==',
  'rhs': 100000,
  'terms': [('prod_I_10', 1), ('inv_I_9', 1), ('inv_I_10', -1)]},
 {'name': 'constraint_005',
  'sense': '==',
  'rhs': 100000,
  'terms': [('prod_I_11', 1), ('inv_I_10', 1), ('inv_I_11', -1)]},
 {'name': 'constraint_006',
  'sense': '==',
  'rhs': 100000,
  'terms': [('prod_I_12', 1), ('inv_I_11', 1), ('inv_I_12', -1)]},
 {'name': 'constraint_007',
  'sense': '==',
  'rhs': 15000,
  'terms': [('prod_II_7', 1), ('inv_II_7', -1)]},
 {'name': 'constraint_008',
  'sense': '==',
  'rhs': 15000,
  'terms': [('prod_II_8', 1), ('inv_II_7', 1), ('inv_II_8', -1)]},
 {'name': 'constraint_009',
  'sense': '==',
  'rhs': 15000,
  'terms': [('prod_II_9', 1), ('inv_II_8', 1), ('inv_II_9', -1)]},
 {'name': 'constraint_010',
  'sense': '>=',
  'rhs': 50000,
  'terms': [('prod_II_10', 1), ('inv_II_9', 1), ('inv_II_10', -1)]},
 {'name': 'constraint_011',
  'sense': '==',
  'rhs': 50000,
  'terms': [('prod_II_11', 1), ('inv_II_10', 1), ('inv_II_11', -1)]},
 {'name': 'constraint_012',
  'sense': '==',
  'rhs': 50000,
  'terms': [('prod_II_12', 1), ('inv_II_11', 1), ('inv_II_12', -1)]},
 {'name': 'constraint_013',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_7', 1), ('prod_II_7', 1)]},
 {'name': 'constraint_014',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_7', 0.2),
            ('inv_II_7', 0.4),
            ('own_storage_7', -1),
            ('external_storage_7', -1)]},
 {'name': 'constraint_015', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_7', 1)]},
 {'name': 'constraint_016',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_8', 1), ('prod_II_8', 1)]},
 {'name': 'constraint_017',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_8', 0.2),
            ('inv_II_8', 0.4),
            ('own_storage_8', -1),
            ('external_storage_8', -1)]},
 {'name': 'constraint_018', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_8', 1)]},
 {'name': 'constraint_019',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_9', 1), ('prod_II_9', 1)]},
 {'name': 'constraint_020',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_9', 0.2),
            ('inv_II_9', 0.4),
            ('own_storage_9', -1),
            ('external_storage_9', -1)]},
 {'name': 'constraint_021', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_9', 1)]},
 {'name': 'constraint_022',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_10', 1), ('prod_II_10', 1)]},
 {'name': 'constraint_023',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_10', 0.2),
            ('inv_II_10', 0.4),
            ('own_storage_10', -1),
            ('external_storage_10', -1)]},
 {'name': 'constraint_024', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_10', 1)]},
 {'name': 'constraint_025',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_11', 1), ('prod_II_11', 1)]},
 {'name': 'constraint_026',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_11', 0.2),
            ('inv_II_11', 0.4),
            ('own_storage_11', -1),
            ('external_storage_11', -1)]},
 {'name': 'constraint_027', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_11', 1)]},
 {'name': 'constraint_028',
  'sense': '<=',
  'rhs': 120000,
  'terms': [('prod_I_12', 1), ('prod_II_12', 1)]},
 {'name': 'constraint_029',
  'sense': '==',
  'rhs': 0,
  'terms': [('inv_I_12', 0.2),
            ('inv_II_12', 0.4),
            ('own_storage_12', -1),
            ('external_storage_12', -1)]},
 {'name': 'constraint_030', 'sense': '<=', 'rhs': 15000, 'terms': [('own_storage_12', 1)]}]

OBJECTIVE_TERMS = [('prod_I_7', 4.5),
 ('prod_I_8', 4.5),
 ('prod_I_9', 4.5),
 ('prod_I_10', 4.5),
 ('prod_I_11', 4.5),
 ('prod_I_12', 4.5),
 ('prod_II_7', 7.0),
 ('prod_II_8', 7.0),
 ('prod_II_9', 7.0),
 ('prod_II_10', 7.0),
 ('prod_II_11', 7.0),
 ('prod_II_12', 7.0),
 ('own_storage_7', 1),
 ('external_storage_7', 1.5),
 ('own_storage_8', 1),
 ('external_storage_8', 1.5),
 ('own_storage_9', 1),
 ('external_storage_9', 1.5),
 ('own_storage_10', 1),
 ('external_storage_10', 1.5),
 ('own_storage_11', 1),
 ('external_storage_11', 1.5),
 ('own_storage_12', 1),
 ('external_storage_12', 1.5)]
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
