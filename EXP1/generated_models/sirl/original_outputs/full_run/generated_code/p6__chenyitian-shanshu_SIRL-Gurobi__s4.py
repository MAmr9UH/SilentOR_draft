import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("freight_car_relocation_model")
    
    move_cost = {
        ("1", "2"): data["move_cost"]["1_2"],
        ("1", "3"): data["move_cost"]["1_3"],
        ("1", "4"): data["move_cost"]["1_4"],
        ("1", "5"): data["move_cost"]["1_5"],
        ("2", "1"): data["move_cost"]["2_1"],
        ("2", "3"): data["move_cost"]["2_3"],
        ("2", "4"): data["move_cost"]["2_4"],
        ("2", "5"): data["move_cost"]["2_5"],
        ("3", "1"): data["move_cost"]["3_1"],
        ("3", "2"): data["move_cost"]["3_2"],
        ("3", "4"): data["move_cost"]["3_4"],
        ("3", "5"): data["move_cost"]["3_5"],
        ("4", "1"): data["move_cost"]["4_1"],
        ("4", "2"): data["move_cost"]["4_2"],
        ("4", "3"): data["move_cost"]["4_3"],
        ("4", "5"): data["move_cost"]["4_5"],
        ("5", "1"): data["move_cost"]["5_1"],
        ("5", "2"): data["move_cost"]["5_2"],
        ("5", "3"): data["move_cost"]["5_3"],
        ("5", "4"): data["move_cost"]["5_4"]
    }

    current_cars = {
        "1": data["current_cars"]["1"],
        "2": data["current_cars"]["2"],
        "3": data["current_cars"]["3"],
        "4": data["current_cars"]["4"],
        "5": data["current_cars"]["5"]
    }

    cars_needed = {
        "1": data["cars_needed"]["1"],
        "2": data["cars_needed"]["2"],
        "3": data["cars_needed"]["3"],
        "4": data["cars_needed"]["4"],
        "5": data["cars_needed"]["5"]
    }

    variables = {}

    # Create decision variables
    for (i, j), cost in move_cost.items():
        variables[(i, j)] = model.addVar(name=f"x_{i}_{j}", lb=0, vtype=GRB.CONTINUOUS)

    # Objective function: Minimize total cost of moving cars
    model.setObjective(gp.quicksum(cost * variables[(i, j)] for (i, j), cost in move_cost.items()), GRB.MINIMIZE)

    # Current number of cars in each region
    for i in ["1", "2", "3", "4", "5"]:
        model.addConstr(gp.quicksum(variables[(j, i)] for j in ["1", "2", "3", "4", "5"] if (j, i) in move_cost.keys()) - 
                       gp.quicksum(variables[(i, j)] for j in ["1", "2", "3", "4", "5"] if (i, j) in move_cost.keys()) == 
                       cars_needed[i] - current_cars[i])

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_2": variables[("1", "2")].x,
            "x_1_3": variables[("1", "3")].x,
            "x_1_4": variables[("1", "4")].x,
            "x_1_5": variables[("1", "5")].x,
            "x_2_1": variables[("2", "1")].x,
            "x_2_3": variables[("2", "3")].x,
            "x_2_4": variables[("2", "4")].x,
            "x_2_5": variables[("2", "5")].x,
            "x_3_1": variables[("3", "1")].x,
            "x_3_2": variables[("3", "2")].x,
            "x_3_4": variables[("3", "4")].x,
            "x_3_5": variables[("3", "5")].x,
            "x_4_1": variables[("4", "1")].x,
            "x_4_2": variables[("4", "2")].x,
            "x_4_3": variables[("4", "3")].x,
            "x_4_5": variables[("4", "5")].x,
            "x_5_1": variables[("5", "1")].x,
            "x_5_2": variables[("5", "2")].x,
            "x_5_3": variables[("5", "3")].x,
            "x_5_4": variables[("5", "4")].x
        }
        return {
            "status": "OPTIMAL",
            "objective": round(model.objVal),
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {}
        }