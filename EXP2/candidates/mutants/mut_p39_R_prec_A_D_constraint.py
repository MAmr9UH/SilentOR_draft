"""Certified-reference candidate for problem 39.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 'start_A', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_B', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_C', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_D', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_E', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_F', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'start_G', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'Cmax', 'vtype': 'C', 'lb': 0.0, 'ub': None},
 {'name': 'machine_span', 'vtype': 'C', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001', 'sense': '>=', 'rhs': 4, 'terms': [('start_G', 1), ('start_A', -1)]},
 {'name': 'constraint_002', 'sense': '>=', 'rhs': 3.999, 'terms': [('start_D', 1), ('start_A', -1)]},
 {'name': 'constraint_003', 'sense': '>=', 'rhs': 10, 'terms': [('start_F', 1), ('start_E', -1)]},
 {'name': 'constraint_004', 'sense': '>=', 'rhs': 1, 'terms': [('start_F', 1), ('start_G', -1)]},
 {'name': 'constraint_005', 'sense': '>=', 'rhs': 2, 'terms': [('start_C', 1), ('start_D', -1)]},
 {'name': 'constraint_006', 'sense': '>=', 'rhs': 10, 'terms': [('start_C', 1), ('start_F', -1)]},
 {'name': 'constraint_007', 'sense': '>=', 'rhs': 10, 'terms': [('start_B', 1), ('start_F', -1)]},
 {'name': 'constraint_008', 'sense': '>=', 'rhs': 4, 'terms': [('Cmax', 1), ('start_A', -1)]},
 {'name': 'constraint_009', 'sense': '>=', 'rhs': 3, 'terms': [('Cmax', 1), ('start_B', -1)]},
 {'name': 'constraint_010', 'sense': '>=', 'rhs': 5, 'terms': [('Cmax', 1), ('start_C', -1)]},
 {'name': 'constraint_011', 'sense': '>=', 'rhs': 2, 'terms': [('Cmax', 1), ('start_D', -1)]},
 {'name': 'constraint_012', 'sense': '>=', 'rhs': 10, 'terms': [('Cmax', 1), ('start_E', -1)]},
 {'name': 'constraint_013', 'sense': '>=', 'rhs': 10, 'terms': [('Cmax', 1), ('start_F', -1)]},
 {'name': 'constraint_014', 'sense': '>=', 'rhs': 1, 'terms': [('Cmax', 1), ('start_G', -1)]},
 {'name': 'constraint_015',
  'sense': '==',
  'rhs': 3,
  'terms': [('machine_span', 1), ('start_B', -1), ('start_A', 1)]}]

OBJECTIVE_TERMS = [('Cmax', 1000), ('machine_span', 5000)]
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
