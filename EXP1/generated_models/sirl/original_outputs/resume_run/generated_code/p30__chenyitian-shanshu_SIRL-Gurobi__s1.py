import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("investment_model")
    
    x_annual_y1 = model.addVar(name="x_annual_y1", vtype=GRB.CONTINUOUS, lb=0)
    x_annual_y2 = model.addVar(name="x_annual_y2", vtype=GRB.CONTINUOUS, lb=0)
    x_annual_y3 = model.addVar(name="x_annual_y3", vtype=GRB.CONTINUOUS, lb=0)
    x_project2_y1 = model.addVar(name="x_project2_y1", vtype=GRB.CONTINUOUS, lb=0, ub=data["project2_limit"])
    x_project3_y2 = model.addVar(name="x_project3_y2", vtype=GRB.CONTINUOUS, lb=0, ub=data["project3_limit"])
    x_project4_y3 = model.addVar(name="x_project4_y3", vtype=GRB.CONTINUOUS, lb=0, ub=data["project4_limit"])
    cash_after_y1 = model.addVar(name="cash_after_y1", vtype=GRB.CONTINUOUS, lb=0)
    cash_after_y2 = model.addVar(name="cash_after_y2", vtype=GRB.CONTINUOUS, lb=0)
    cash_after_y3 = model.addVar(name="cash_after_y3", vtype=GRB.CONTINUOUS, lb=0)
    final_amount = model.addVar(name="final_amount", vtype=GRB.CONTINUOUS, lb=0)

    variables = {
        "x_annual_y1": x_annual_y1,
        "x_annual_y2": x_annual_y2,
        "x_annual_y3": x_annual_y3,
        "x_project2_y1": x_project2_y1,
        "x_project3_y2": x_project3_y2,
        "x_project4_y3": x_project4_y3,
        "cash_after_y1": cash_after_y1,
        "cash_after_y2": cash_after_y2,
        "cash_after_y3": cash_after_y3,
        "final_amount": final_amount
    }

    # Initial fund
    model.addConstr(cash_after_y1 == data["initial_fund"] - x_annual_y1 - x_project2_y1)

    # Year 1 investment returns
    model.addConstr(cash_after_y1 * data["annual_project_return"] == x_annual_y1 * data["annual_project_return"] + x_project2_y1 * data["project2_return"])

    # Year 2 investment returns
    model.addConstr(cash_after_y1 * data["annual_project_return"] - x_annual_y2 - x_project3_y2 == cash_after_y2)
    model.addConstr(cash_after_y2 * data["annual_project_return"] == x_annual_y2 * data["annual_project_return"] + x_project3_y2 * data["project3_return"])

    # Year 3 investment returns
    model.addConstr(cash_after_y2 * data["annual_project_return"] - x_annual_y3 - x_project4_y3 == cash_after_y3)
    model.addConstr(cash_after_y3 * data["annual_project_return"] == x_annual_y3 * data["annual_project_return"] + x_project4_y3 * data["project4_return"])

    # Final amount at the end of year 3
    model.addConstr(final_amount == cash_after_y3 * data["annual_project_return"])

    model.setObjective(final_amount, GRB.MAXIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_annual_y1": variables["x_annual_y1"].x,
            "x_annual_y2": variables["x_annual_y2"].x,
            "x_annual_y3": variables["x_annual_y3"].x,
            "x_project2_y1": variables["x_project2_y1"].x,
            "x_project3_y2": variables["x_project3_y2"].x,
            "x_project4_y3": variables["x_project4_y3"].x,
            "cash_after_y1": variables["cash_after_y1"].x,
            "cash_after_y2": variables["cash_after_y2"].x,
            "cash_after_y3": variables["cash_after_y3"].x,
            "final_amount": variables["final_amount"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }