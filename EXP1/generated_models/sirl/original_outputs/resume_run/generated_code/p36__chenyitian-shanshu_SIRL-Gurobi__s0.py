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
    num_months = len(months)

    variables = {}

    # x_s_l: number of contracts starting in month s with length l
    for s in months:
        for l in contract_lengths:
            variables[f"x_{s}_{l}"] = model.addVar(name=f"x_{s}_{l}", vtype=GRB.INTEGER, lb=0)

    # y_l: binary variable indicating if contract length l is used
    for l in contract_lengths:
        variables[f"y_{l}"] = model.addVar(name=f"y_{l}", vtype=GRB.BINARY)

    # Objective function: Minimize total rental cost
    model.setObjective(
        gp.quicksum(fee_per_100sqm_by_length[l] * variables[f"x_{s}_{l}"] for s in months for l in contract_lengths),
        GRB.MINIMIZE)

    # Demand constraint
    for s in months:
        model.addConstr(gp.quicksum(variables[f"x_{s}_{l}"] * l for l in contract_lengths if (s, l) in feasible_start_length_pairs) >= demand[str(s)])

    # At least two different contract lengths are used
    model.addConstr(gp.quicksum(variables[f"y_{l}"] for l in contract_lengths) >= min_distinct_lengths)

    # At most three different contract lengths are used
    model.addConstr(gp.quicksum(variables[f"y_{l}"] for l in contract_lengths) <= max_distinct_lengths)

    # If a 4-month contract is chosen, no 1-month contract may be chosen
    model.addConstr(variables["y_1"] + variables["y_4"] <= 1)

    # Linking x_s_l to y_l
    for l in contract_lengths:
        for s in months:
            if (s, l) in feasible_start_length_pairs:
                model.addConstr(variables[f"x_{s}_{l}"] <= variables[f"y_{l}"])

    model.update()

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_1": variables["x_1_1"].x,
            "x_1_2": variables["x_1_2"].x,
            "x_1_3": variables["x_1_3"].x,
            "x_1_4": variables["x_1_4"].x,
            "x_2_1": variables["x_2_1"].x,
            "x_2_2": variables["x_2_2"].x,
            "x_2_3": variables["x_2_3"].x,
            "x_3_1": variables["x_3_1"].x,
            "x_3_2": variables["x_3_2"].x,
            "x_4_1": variables["x_4_1"].x,
            "y_1": variables["y_1"].x,
            "y_2": variables["y_2"].x,
            "y_3": variables["y_3"].x,
            "y_4": variables["y_4"].x
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