"""Certified-reference candidate for problem 9.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 's0', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's3', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's4', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's5', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's6', 'vtype': 'I', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '>=',
  'rhs': 15,
  'terms': [('s0', 1), ('s6', 1), ('s5', 1), ('s4', 1), ('s3', 1)]},
 {'name': 'constraint_002',
  'sense': '>=',
  'rhs': 13,
  'terms': [('s1', 1), ('s0', 1), ('s6', 1), ('s5', 1), ('s4', 1)]},
 {'name': 'constraint_003',
  'sense': '>=',
  'rhs': 15,
  'terms': [('s2', 1), ('s1', 1), ('s0', 1), ('s6', 1), ('s5', 1)]},
 {'name': 'constraint_004',
  'sense': '>=',
  'rhs': 18,
  'terms': [('s3', 1), ('s2', 1), ('s1', 1), ('s0', 1), ('s6', 1)]},
 {'name': 'constraint_005',
  'sense': '>=',
  'rhs': 14,
  'terms': [('s4', 1), ('s3', 1), ('s2', 1), ('s1', 1), ('s0', 1)]},
 {'name': 'constraint_006',
  'sense': '>=',
  'rhs': 16,
  'terms': [('s5', 1), ('s4', 1), ('s3', 1), ('s2', 1), ('s1', 1)]},
 {'name': 'constraint_007',
  'sense': '>=',
  'rhs': 10,
  'terms': [('s6', 1), ('s5', 1), ('s4', 1), ('s3', 1), ('s2', 1)]}]

OBJECTIVE_TERMS = [('s0', 0.0), ('s1', 1), ('s2', 1), ('s3', 1), ('s4', 1), ('s5', 1), ('s6', 1)]
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
