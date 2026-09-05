"""Certified-reference candidate for problem 8.

The complete formulation is explicit below.  It contains no gold objective or hidden
mutation/certification information.
"""
import gurobipy as gp
from gurobipy import GRB


VARIABLE_SPECS = [{'name': 's1', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's2', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's3', 'vtype': 'I', 'lb': 0.0, 'ub': None},
 {'name': 's4', 'vtype': 'I', 'lb': 0.0, 'ub': None}]

CONSTRAINT_SPECS = [{'name': 'constraint_001', 'sense': '>=', 'rhs': 55, 'terms': [('s1', 1), ('s4', 1)]},
 {'name': 'constraint_002', 'sense': '>=', 'rhs': 46, 'terms': [('s1', 1)]},
 {'name': 'constraint_003', 'sense': '>=', 'rhs': 59, 'terms': [('s1', 1), ('s2', 1)]},
 {'name': 'constraint_004', 'sense': '>=', 'rhs': 23, 'terms': [('s2', 1)]},
 {'name': 'constraint_005', 'sense': '>=', 'rhs': 60, 'terms': [('s2', 1), ('s3', 1)]},
 {'name': 'constraint_006', 'sense': '>=', 'rhs': 38, 'terms': [('s3', 1)]},
 {'name': 'constraint_007', 'sense': '>=', 'rhs': 20, 'terms': [('s3', 1), ('s4', 1)]},
 {'name': 'constraint_008', 'sense': '>=', 'rhs': 30, 'terms': [('s4', 1)]}]

OBJECTIVE_TERMS = [('s1', 136.0), ('s2', 140), ('s3', 190), ('s4', 188)]
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
