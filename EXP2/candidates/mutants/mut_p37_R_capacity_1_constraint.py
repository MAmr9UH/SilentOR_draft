"""Certified-reference candidate for problem 37.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'buy_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'buy_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'buy_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'sell_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'sell_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'sell_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inventory_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inventory_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'inventory_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'cash_1', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'cash_2', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'cash_3', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'profit', 'vtype': 'C', 'lb': None, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001',
  'sense': '==',
  'rhs': 1000,
  'terms': [('inventory_1', 1), ('buy_1', -1), ('sell_1', 1)]},
 {'name': 'constraint_002',
  'sense': '==',
  'rhs': 0,
  'terms': [('inventory_2', 1), ('inventory_1', -1), ('buy_2', -1), ('sell_2', 1)]},
 {'name': 'constraint_003',
  'sense': '==',
  'rhs': 0,
  'terms': [('inventory_3', 1), ('inventory_2', -1), ('buy_3', -1), ('sell_3', 1)]},
 {'name': 'constraint_004', 'sense': '<=', 'rhs': 1000, 'terms': [('sell_1', 1)]},
 {'name': 'constraint_005', 'sense': '<=', 'rhs': 0, 'terms': [('sell_2', 1), ('inventory_1', -1)]},
 {'name': 'constraint_006', 'sense': '<=', 'rhs': 0, 'terms': [('sell_3', 1), ('inventory_2', -1)]},
 {'name': 'constraint_007', 'sense': '<=', 'rhs': 5000.001, 'terms': [('inventory_1', 1)]},
 {'name': 'constraint_008', 'sense': '<=', 'rhs': 5000, 'terms': [('inventory_2', 1)]},
 {'name': 'constraint_009', 'sense': '<=', 'rhs': 5000, 'terms': [('inventory_3', 1)]},
 {'name': 'constraint_010', 'sense': '==', 'rhs': 2000, 'terms': [('inventory_3', 1)]},
 {'name': 'constraint_011',
  'sense': '==',
  'rhs': 20000,
  'terms': [('cash_1', 1), ('buy_1', 2.85), ('sell_1', -3.1)]},
 {'name': 'constraint_012',
  'sense': '==',
  'rhs': 0,
  'terms': [('cash_2', 1), ('cash_1', -1), ('buy_2', 3.05), ('sell_2', -3.25)]},
 {'name': 'constraint_013',
  'sense': '==',
  'rhs': 0,
  'terms': [('cash_3', 1), ('cash_2', -1), ('buy_3', 2.9), ('sell_3', -2.95)]},
 {'name': 'constraint_014', 'sense': '==', 'rhs': 20000, 'terms': [('cash_3', 1), ('profit', -1)]}]

OBJECTIVE_TERMS = [('profit', 1)]
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
