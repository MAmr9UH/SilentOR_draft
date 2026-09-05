"""Certified-reference candidate for problem 40.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'y1_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y1_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y2_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y2_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y3_A', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'y3_B', 'vtype': 'B', 'lb': 0.0, 'ub': 1.0},
 {'name': 'skilled_t1_A', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'skilled_t1_B', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'skilled_t2_A', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'skilled_t3_B', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'labor_t1_B', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'labor_t2_B', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'labor_t3_A', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'labor_t3_B', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'total_skilled', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 'total_labor', 'vtype': 'I', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001', 'sense': '==', 'rhs': 1, 'terms': [('y1_A', 1), ('y1_B', 1)]},
 {'name': 'constraint_002', 'sense': '==', 'rhs': 1, 'terms': [('y2_A', 1), ('y2_B', 1)]},
 {'name': 'constraint_003', 'sense': '==', 'rhs': 1, 'terms': [('y3_A', 1), ('y3_B', 1)]},
 {'name': 'constraint_004',
  'sense': '>=',
  'rhs': 0,
  'terms': [('skilled_t1_A', 1), ('y1_A', -200)]},
 {'name': 'constraint_005',
  'sense': '>=',
  'rhs': 0,
  'terms': [('skilled_t1_B', 1), ('y1_B', -200)]},
 {'name': 'constraint_006', 'sense': '>=', 'rhs': 0, 'terms': [('labor_t1_B', 1), ('y1_B', -400)]},
 {'name': 'constraint_007',
  'sense': '>=',
  'rhs': 0,
  'terms': [('skilled_t2_A', 1), ('y2_A', -257.14285714285717)]},
 {'name': 'constraint_008', 'sense': '>=', 'rhs': 0, 'terms': [('labor_t2_B', 1), ('y2_B', -300)]},
 {'name': 'constraint_009', 'sense': '>=', 'rhs': 0, 'terms': [('labor_t3_A', 1), ('y3_A', -500)]},
 {'name': 'constraint_010',
  'sense': '>=',
  'rhs': 0,
  'terms': [('skilled_t3_B', 1), ('y3_B', -120)]},
 {'name': 'constraint_011', 'sense': '>=', 'rhs': 0, 'terms': [('labor_t3_B', 1), ('y3_B', -360)]},
 {'name': 'constraint_012', 'sense': '>=', 'rhs': 0, 'terms': [('skilled_t3_B', 1), ('y3_B', -20)]},
 {'name': 'constraint_013', 'sense': '<=', 'rhs': 1, 'terms': [('y1_B', 1), ('y3_A', 1)]},
 {'name': 'constraint_014',
  'sense': '==',
  'rhs': 0,
  'terms': [('total_skilled', 1),
            ('skilled_t1_A', -1),
            ('skilled_t1_B', -1),
            ('skilled_t2_A', -1),
            ('skilled_t3_B', -1)]},
 {'name': 'constraint_015',
  'sense': '==',
  'rhs': 0,
  'terms': [('total_labor', 1),
            ('labor_t1_B', -1),
            ('labor_t2_B', -1),
            ('labor_t3_A', -1),
            ('labor_t3_B', -1)]},
 {'name': 'constraint_016', 'sense': '<=', 'rhs': 401.0, 'terms': [('total_skilled', 1)]},
 {'name': 'constraint_017', 'sense': '<=', 'rhs': 800, 'terms': [('total_labor', 1)]},
 {'name': 'constraint_018',
  'sense': '<=',
  'rhs': 0,
  'terms': [('total_skilled', 1), ('total_labor', -0.6)]},
 {'name': 'constraint_019', 'sense': '<=', 'rhs': 1, 'terms': [('y1_A', 1)]},
 {'name': 'constraint_020', 'sense': '<=', 'rhs': 1, 'terms': [('y1_B', 1)]},
 {'name': 'constraint_021', 'sense': '<=', 'rhs': 1, 'terms': [('y2_A', 1)]},
 {'name': 'constraint_022', 'sense': '<=', 'rhs': 1, 'terms': [('y2_B', 1)]},
 {'name': 'constraint_023', 'sense': '<=', 'rhs': 1, 'terms': [('y3_A', 1)]},
 {'name': 'constraint_024', 'sense': '<=', 'rhs': 1, 'terms': [('y3_B', 1)]}]

OBJECTIVE_TERMS = [('skilled_t1_A', 100),
 ('skilled_t1_B', 100),
 ('skilled_t2_A', 100),
 ('skilled_t3_B', 100),
 ('labor_t1_B', 80),
 ('labor_t2_B', 80),
 ('labor_t3_A', 80),
 ('labor_t3_B', 80),
 ('y1_B', 500)]
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
