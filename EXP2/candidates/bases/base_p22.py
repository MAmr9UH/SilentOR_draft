"""Certified-reference candidate for problem 22.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'z', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'x_A_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_A_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_A_E', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_B_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_B_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_B_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_B_E', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_C_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_C_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_C_E', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_D_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_D_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_D_C', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_D_E', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_E_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'x_E_D', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_A_B', 1), ('x_A_C', 1), ('x_A_E', 1), ('x_B_A', -1), ('x_C_A', -1), ('x_D_A', -1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_A_E', 1), ('x_B_E', 1), ('x_C_E', 1), ('x_D_E', 1), ('x_E_B', -1), ('x_E_D', -1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_A_C', 1), ('x_B_C', 1), ('x_D_C', 1)]},
 {'name': 'constraint_004',
  'sense': '==',
  'rhs': 1,
  'terms': [('x_C_A', 1), ('x_C_D', 1), ('x_C_E', 1)]},
 {'name': 'constraint_005',
  'sense': '==',
  'rhs': 0,
  'terms': [('x_A_B', 1),
            ('x_D_B', 1),
            ('x_E_B', 1),
            ('x_B_A', -1),
            ('x_B_C', -1),
            ('x_B_D', -1),
            ('x_B_E', -1)]},
 {'name': 'constraint_006',
  'sense': '==',
  'rhs': 0,
  'terms': [('x_B_D', 1),
            ('x_C_D', 1),
            ('x_E_D', 1),
            ('x_D_A', -1),
            ('x_D_B', -1),
            ('x_D_C', -1),
            ('x_D_E', -1)]},
 {'name': 'constraint_007',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_B_A', 1), ('x_C_A', 1), ('x_D_A', 1)]},
 {'name': 'constraint_008',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_A_B', 1), ('x_A_C', 1), ('x_A_E', 1)]},
 {'name': 'constraint_009',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_A_B', 1), ('x_D_B', 1), ('x_E_B', 1)]},
 {'name': 'constraint_010',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_B_A', 1), ('x_B_C', 1), ('x_B_D', 1), ('x_B_E', 1)]},
 {'name': 'constraint_011',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_A_C', 1), ('x_B_C', 1), ('x_D_C', 1)]},
 {'name': 'constraint_012',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_C_A', 1), ('x_C_D', 1), ('x_C_E', 1)]},
 {'name': 'constraint_013',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_B_D', 1), ('x_C_D', 1), ('x_E_D', 1)]},
 {'name': 'constraint_014',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_D_A', 1), ('x_D_B', 1), ('x_D_C', 1), ('x_D_E', 1)]},
 {'name': 'constraint_015',
  'sense': '<=',
  'rhs': 1,
  'terms': [('x_A_E', 1), ('x_B_E', 1), ('x_C_E', 1), ('x_D_E', 1)]},
 {'name': 'constraint_016', 'sense': '<=', 'rhs': 1, 'terms': [('x_E_B', 1), ('x_E_D', 1)]},
 {'name': 'constraint_017', 'sense': '<=', 'rhs': 190, 'terms': [('z', 1), ('x_A_B', 100)]},
 {'name': 'constraint_018', 'sense': '<=', 'rhs': 185, 'terms': [('z', 1), ('x_A_C', 100)]},
 {'name': 'constraint_019', 'sense': '<=', 'rhs': 165, 'terms': [('z', 1), ('x_A_E', 100)]},
 {'name': 'constraint_020', 'sense': '<=', 'rhs': 195, 'terms': [('z', 1), ('x_B_A', 100)]},
 {'name': 'constraint_021', 'sense': '<=', 'rhs': 170, 'terms': [('z', 1), ('x_B_C', 100)]},
 {'name': 'constraint_022', 'sense': '<=', 'rhs': 165, 'terms': [('z', 1), ('x_B_D', 100)]},
 {'name': 'constraint_023', 'sense': '<=', 'rhs': 134, 'terms': [('z', 1), ('x_B_E', 100)]},
 {'name': 'constraint_024', 'sense': '<=', 'rhs': 160, 'terms': [('z', 1), ('x_C_A', 100)]},
 {'name': 'constraint_025', 'sense': '<=', 'rhs': 188, 'terms': [('z', 1), ('x_C_D', 100)]},
 {'name': 'constraint_026', 'sense': '<=', 'rhs': 180, 'terms': [('z', 1), ('x_C_E', 100)]},
 {'name': 'constraint_027', 'sense': '<=', 'rhs': 167, 'terms': [('z', 1), ('x_D_A', 100)]},
 {'name': 'constraint_028', 'sense': '<=', 'rhs': 130, 'terms': [('z', 1), ('x_D_B', 100)]},
 {'name': 'constraint_029', 'sense': '<=', 'rhs': 125, 'terms': [('z', 1), ('x_D_C', 100)]},
 {'name': 'constraint_030', 'sense': '<=', 'rhs': 184, 'terms': [('z', 1), ('x_D_E', 100)]},
 {'name': 'constraint_031', 'sense': '<=', 'rhs': 151, 'terms': [('z', 1), ('x_E_B', 100)]},
 {'name': 'constraint_032', 'sense': '<=', 'rhs': 156, 'terms': [('z', 1), ('x_E_D', 100)]},
 {'name': 'constraint_033', 'sense': '<=', 'rhs': 100, 'terms': [('z', 1)]}]

OBJECTIVE_TERMS = [('z', 1)]
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
