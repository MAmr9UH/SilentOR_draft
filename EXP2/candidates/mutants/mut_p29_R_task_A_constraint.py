"""Certified-reference candidate for problem 29.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'x_I_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_I_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_I_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_I_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_II_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_II_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_II_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_II_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_III_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_III_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_III_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_III_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_IV_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_IV_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_IV_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_IV_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_V_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_V_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_V_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_V_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '>=',
  'rhs': 1,
  'terms': [('x_I_A', 1), ('x_II_A', 1), ('x_III_A', 1), ('x_IV_A', 1), ('x_V_A', 1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_I_B', 1), ('x_II_B', 1), ('x_III_B', 1), ('x_IV_B', 1), ('x_V_B', 1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_I_C', 1), ('x_II_C', 1), ('x_III_C', 1), ('x_IV_C', 1), ('x_V_C', 1)]},
 {'name': 'constraint_004',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_I_D', 1), ('x_II_D', 1), ('x_III_D', 1), ('x_IV_D', 1), ('x_V_D', 1)]},
 {'name': 'constraint_005',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_I_A', 1), ('x_I_B', 1), ('x_I_C', 1), ('x_I_D', 1)]},
 {'name': 'constraint_006',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_II_A', 1), ('x_II_B', 1), ('x_II_C', 1), ('x_II_D', 1)]},
 {'name': 'constraint_007',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_III_A', 1), ('x_III_B', 1), ('x_III_C', 1), ('x_III_D', 1)]},
 {'name': 'constraint_008',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_IV_A', 1), ('x_IV_B', 1), ('x_IV_C', 1), ('x_IV_D', 1)]},
 {'name': 'constraint_009',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_V_A', 1), ('x_V_B', 1), ('x_V_C', 1), ('x_V_D', 1)]},
 {'name': 'constraint_010', 'sense': '<=', 'rhs': 1, 'terms': [('x_I_A', 1)]},
 {'name': 'constraint_011', 'sense': '<=', 'rhs': 1, 'terms': [('x_I_B', 1)]},
 {'name': 'constraint_012', 'sense': '<=', 'rhs': 1, 'terms': [('x_I_C', 1)]},
 {'name': 'constraint_013', 'sense': '<=', 'rhs': 1, 'terms': [('x_I_D', 1)]},
 {'name': 'constraint_014', 'sense': '<=', 'rhs': 1, 'terms': [('x_II_A', 1)]},
 {'name': 'constraint_015', 'sense': '<=', 'rhs': 1, 'terms': [('x_II_B', 1)]},
 {'name': 'constraint_016', 'sense': '<=', 'rhs': 1, 'terms': [('x_II_C', 1)]},
 {'name': 'constraint_017', 'sense': '<=', 'rhs': 1, 'terms': [('x_II_D', 1)]},
 {'name': 'constraint_018', 'sense': '<=', 'rhs': 1, 'terms': [('x_III_A', 1)]},
 {'name': 'constraint_019', 'sense': '<=', 'rhs': 1, 'terms': [('x_III_B', 1)]},
 {'name': 'constraint_020', 'sense': '<=', 'rhs': 1, 'terms': [('x_III_C', 1)]},
 {'name': 'constraint_021', 'sense': '<=', 'rhs': 1, 'terms': [('x_III_D', 1)]},
 {'name': 'constraint_022', 'sense': '<=', 'rhs': 1, 'terms': [('x_IV_A', 1)]},
 {'name': 'constraint_023', 'sense': '<=', 'rhs': 1, 'terms': [('x_IV_B', 1)]},
 {'name': 'constraint_024', 'sense': '<=', 'rhs': 1, 'terms': [('x_IV_C', 1)]},
 {'name': 'constraint_025', 'sense': '<=', 'rhs': 1, 'terms': [('x_IV_D', 1)]},
 {'name': 'constraint_026', 'sense': '<=', 'rhs': 1, 'terms': [('x_V_A', 1)]},
 {'name': 'constraint_027', 'sense': '<=', 'rhs': 1, 'terms': [('x_V_B', 1)]},
 {'name': 'constraint_028', 'sense': '<=', 'rhs': 1, 'terms': [('x_V_C', 1)]},
 {'name': 'constraint_029', 'sense': '<=', 'rhs': 1, 'terms': [('x_V_D', 1)]}]

OBJECTIVE_TERMS = [('x_I_A', 9),
 ('x_I_B', 4),
 ('x_I_C', 3),
 ('x_I_D', 7),
 ('x_II_A', 4),
 ('x_II_B', 6),
 ('x_II_C', 5),
 ('x_II_D', 6),
 ('x_III_A', 5),
 ('x_III_B', 4),
 ('x_III_C', 7),
 ('x_III_D', 5),
 ('x_IV_A', 7),
 ('x_IV_B', 5),
 ('x_IV_C', 2),
 ('x_IV_D', 3),
 ('x_V_A', 10),
 ('x_V_B', 6),
 ('x_V_C', 7),
 ('x_V_D', 4)]
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
