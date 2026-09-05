import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("warehouse_rental_model")

    demand = data["demand_100sqm"]
    contract_lengths = data["contract_lengths"]
    fee_per_100sqm_by_length = data["fee_per_100sqm_by_length"]
    feasible_start_length_pairs = data["feasible_start_length_pairs"]
    min_distinct_lengths = data["min_distinct_lengths"]
    max_distinct_lengths = data["max_distinct_lengths"]
    mutually_exclusive_lengths = data["mutually_exclusive_lengths"]

    months = data["months"]
    number_of_months = len(months)

    # Decision variables
    x = {}
    for start_month in months:
        for length in contract_lengths:
            x[start_month, length] = model.addVar(name=f"x_{start_month}_{length}", vtype=GRB.INTEGER, lb=0)

    y = {}
    for length in contract_lengths:
        y[length] = model.addVar(name=f"y_{length}", vtype=GRB.BINARY)

    # Objective function: Minimize total rental cost
    total_rental_cost = gp.quicksum(fee_per_100sqm_by_length[length] * x[start_month, length] for start_month in months for length in contract_lengths)
    model.setObjective(total_rental_cost, GRB.MINIMIZE)

    # Demand constraint
    for month in months:
        demand_in_100sqm = demand[str(month)]
        model.addConstr(gp.quicksum(x[start_month, length] * length for start_month in months for length in contract_lengths if start_month <= month and (start_month, length) in feasible_start_length_pairs) >= demand_in_100sqm)

    # At least two different contract lengths
    model.addConstr(gp.quicksum(y[length] for length in contract_lengths) >= min_distinct_lengths)

    # At most three different contract lengths
    model.addConstr(gp.quicksum(y[length] for length in contract_lengths) <= max_distinct_lengths)

    # If a 4-month contract is chosen, no 1-month contract may be chosen
    model.addConstr(y[1] + y[4] <= 1)

    # Solve the model
    return model, x, y

def solve(data: dict) -> dict:
    model, x, y = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_1": x[1, 1].x,
            "x_1_2": x[1, 2].x,
            "x_1_3": x[1, 3].x,
            "x_1_4": x[1, 4].x,
            "x_2_1": x[2, 1].x,
            "x_2_2": x[2, 2].x,
            "x_2_3": x[2, 3].x,
            "x_3_1": x[3, 1].x,
            "x_3_2": x[3, 2].x,
            "x_4_1": x[4, 1].x,
            "y_1": y[1].x,
            "y_2": y[2].x,
            "y_3": y[3].x,
            "y_4": y[4].x
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