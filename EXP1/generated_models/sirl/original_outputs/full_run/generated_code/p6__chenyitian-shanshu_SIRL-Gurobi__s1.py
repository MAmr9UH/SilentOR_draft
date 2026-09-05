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

    variables_keys = {
        "x_1_2": "continuous Var: cars moved from region 1 to region 2",
        "x_1_3": "continuous Var: cars moved from region 1 to region 3",
        "x_1_4": "continuous Var: cars moved from region 1 to region 4",
        "x_1_5": "continuous Var: cars moved from region 1 to region 5",
        "x_2_1": "continuous Var: cars moved from region 2 to region 1",
        "x_2_3": "continuous Var: cars moved from region 2 to region 3",
        "x_2_4": "continuous Var: cars moved from region 2 to region 4",
        "x_2_5": "continuous Var: cars moved from region 2 to region 5",
        "x_3_1": "continuous Var: cars moved from region 3 to region 1",
        "x_3_2": "continuous Var: cars moved from region 3 to region 2",
        "x_3_4": "continuous Var: cars moved from region 3 to region 4",
        "x_3_5": "continuous Var: cars moved from region 3 to region 5",
        "x_4_1": "continuous Var: cars moved from region 4 to region 1",
        "x_4_2": "continuous Var: cars moved from region 4 to region 2",
        "x_4_3": "continuous Var: cars moved from region 4 to region 3",
        "x_4_5": "continuous Var: cars moved from region 4 to region 5",
        "x_5_1": "continuous Var: cars moved from region 5 to region 1",
        "x_5_2": "continuous Var: cars moved from region 5 to region 2",
        "x_5_3": "continuous Var: cars moved from region 5 to region 3",
        "x_5_4": "continuous Var: cars moved from region 5 to region 4"
    }

    variables = {
        "x_1_2": model.addVar(name="x_1_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_3": model.addVar(name="x_1_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_4": model.addVar(name="x_1_4", vtype=GRB.CONTINUOUS, lb=0),
        "x_1_5": model.addVar(name="x_1_5", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_1": model.addVar(name="x_2_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_3": model.addVar(name="x_2_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_4": model.addVar(name="x_2_4", vtype=GRB.CONTINUOUS, lb=0),
        "x_2_5": model.addVar(name="x_2_5", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_1": model.addVar(name="x_3_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_2": model.addVar(name="x_3_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_4": model.addVar(name="x_3_4", vtype=GRB.CONTINUOUS, lb=0),
        "x_3_5": model.addVar(name="x_3_5", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_1": model.addVar(name="x_4_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_2": model.addVar(name="x_4_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_3": model.addVar(name="x_4_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_4_5": model.addVar(name="x_4_5", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_1": model.addVar(name="x_5_1", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_2": model.addVar(name="x_5_2", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_3": model.addVar(name="x_5_3", vtype=GRB.CONTINUOUS, lb=0),
        "x_5_4": model.addVar(name="x_5_4", vtype=GRB.CONTINUOUS, lb=0)
    }

    # Objective function: Minimize total cost of moving cars
    model.setObjective(
        gp.quicksum(move_cost[(str(i), str(j))] * variables[f"x_{i}_{j}"] for (i, j) in move_cost.keys()),
        GRB.MINIMIZE)

    # Region 1: Start with 115 cars, need 300 cars
    model.addConstr(current_cars["1"] - variables["x_1_2"] - variables["x_1_3"] - variables["x_1_4"] - variables["x_1_5"] >= cars_needed["1"])

    # Region 2: Start with 385 cars, need 400 cars
    model.addConstr(current_cars["2"] - variables["x_2_1"] - variables["x_2_3"] - variables["x_2_4"] - variables["x_2_5"] <= cars_needed["2"])

    # Region 3: Start with 410 cars, need 800 cars
    model.addConstr(current_cars["3"] - variables["x_3_1"] - variables["x_3_2"] - variables["x_3_4"] - variables["x_3_5"] >= cars_needed["3"])

    # Region 4: Start with 480 cars, need 200 cars
    model.addConstr(current_cars["4"] - variables["x_4_1"] - variables["x_4_2"] - variables["x_4_3"] - variables["x_4_5"] <= cars_needed["4"])

    # Region 5: Start with 610 cars, need 300 cars
    model.addConstr(current_cars["5"] - variables["x_5_1"] - variables["x_5_2"] - variables["x_5_3"] - variables["x_5_4"] <= cars_needed["5"])

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_2": round(variables["x_1_2"].x),
            "x_1_3": round(variables["x_1_3"].x),
            "x_1_4": round(variables["x_1_4"].x),
            "x_1_5": round(variables["x_1_5"].x),
            "x_2_1": round(variables["x_2_1"].x),
            "x_2_3": round(variables["x_2_3"].x),
            "x_2_4": round(variables["x_2_4"].x),
            "x_2_5": round(variables["x_2_5"].x),
            "x_3_1": round(variables["x_3_1"].x),
            "x_3_2": round(variables["x_3_2"].x),
            "x_3_4": round(variables["x_3_4"].x),
            "x_3_5": round(variables["x_3_5"].x),
            "x_4_1": round(variables["x_4_1"].x),
            "x_4_2": round(variables["x_4_2"].x),
            "x_4_3": round(variables["x_4_3"].x),
            "x_4_5": round(variables["x_4_5"].x),
            "x_5_1": round(variables["x_5_1"].x),
            "x_5_2": round(variables["x_5_2"].x),
            "x_5_3": round(variables["x_5_3"].x),
            "x_5_4": round(variables["x_5_4"].x)
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
            "solution": None
        }