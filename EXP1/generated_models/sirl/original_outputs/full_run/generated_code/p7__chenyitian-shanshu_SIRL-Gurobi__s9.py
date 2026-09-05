import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("factory_production_model")
    
    # Decision variables
    x = {
        "I": {
            1: model.addVar(name="x_I_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="x_I_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="x_I_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="x_I_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "II": {
            1: model.addVar(name="x_II_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="x_II_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="x_II_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="x_II_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "III": {
            1: model.addVar(name="x_III_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="x_III_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="x_III_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="x_III_4", vtype=GRB.CONTINUOUS, lb=0)
        }
    }
    
    inventory = {
        "I": {
            1: model.addVar(name="Iv_I_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Iv_I_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Iv_I_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Iv_I_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "II": {
            1: model.addVar(name="Iv_II_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Iv_II_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Iv_II_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Iv_II_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "III": {
            1: model.addVar(name="Iv_III_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Iv_III_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Iv_III_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Iv_III_4", vtype=GRB.CONTINUOUS, lb=0)
        }
    }
    
    backlog = {
        "I": {
            1: model.addVar(name="Bk_I_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Bk_I_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Bk_I_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Bk_I_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "II": {
            1: model.addVar(name="Bk_II_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Bk_II_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Bk_II_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Bk_II_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "III": {
            1: model.addVar(name="Bk_III_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="Bk_III_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="Bk_III_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="Bk_III_4", vtype=GRB.CONTINUOUS, lb=0)
        }
    }
    
    # Objective function: Minimize total late-penalty and storage cost
    late_penalty = {
        "I": {
            1: model.addVar(name="late_penalty_I_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="late_penalty_I_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="late_penalty_I_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="late_penalty_I_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "II": {
            1: model.addVar(name="late_penalty_II_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="late_penalty_II_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="late_penalty_II_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="late_penalty_II_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "III": {
            1: model.addVar(name="late_penalty_III_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="late_penalty_III_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="late_penalty_III_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="late_penalty_III_4", vtype=GRB.CONTINUOUS, lb=0)
        }
    }
    
    storage_cost = {
        "I": {
            1: model.addVar(name="storage_cost_I_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="storage_cost_I_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="storage_cost_I_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="storage_cost_I_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "II": {
            1: model.addVar(name="storage_cost_II_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="storage_cost_II_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="storage_cost_II_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="storage_cost_II_4", vtype=GRB.CONTINUOUS, lb=0)
        },
        "III": {
            1: model.addVar(name="storage_cost_III_1", vtype=GRB.CONTINUOUS, lb=0),
            2: model.addVar(name="storage_cost_III_2", vtype=GRB.CONTINUOUS, lb=0),
            3: model.addVar(name="storage_cost_III_3", vtype=GRB.CONTINUOUS, lb=0),
            4: model.addVar(name="storage_cost_III_4", vtype=GRB.CONTINUOUS, lb=0)
        }
    }
    
    # Define orders
    orders = {
        "I": {
            1: data["orders"]["I_1"],
            2: data["orders"]["I_2"],
            3: data["orders"]["I_3"],
            4: data["orders"]["I_4"]
        },
        "II": {
            1: data["orders"]["II_1"],
            2: data["orders"]["II_2"],
            3: data["orders"]["II_3"],
            4: data["orders"]["II_4"]
        },
        "III": {
            1: data["orders"]["III_1"],
            2: data["orders"]["III_2"],
            3: data["orders"]["III_3"],
            4: data["orders"]["III_4"]
        }
    }
    
    # Define hours per unit
    hours_per_unit = {
        "I": data["hours_per_unit"]["I"],
        "II": data["hours_per_unit"]["II"],
        "III": data["hours_per_unit"]["III"]
    }
    
    # Define capacity hours per quarter
    capacity_hours_per_quarter = data["capacity_hours_per_quarter"]
    
    # Define late penalty per unit per quarter
    late_penalty_per_unit_per_quarter = {
        "I": data["late_penalty_per_unit_per_quarter"]["I"],
        "II": data["late_penalty_per_unit_per_quarter"]["II"],
        "III": data["late_penalty_per_unit_per_quarter"]["III"]
    }
    
    # Define storage cost per unit per quarter
    storage_cost_per_unit_per_quarter = data["storage_cost_per_unit_per_quarter"]
    
    # Define product I blocked quarter
    product_I_blocked_quarter = data["product_I_blocked_quarter"]
    
    # Constraints
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            model.addConstr(x[product][quarter] * hours_per_unit[product] <= capacity_hours_per_quarter)
    
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            if product == "I" and quarter == product_I_blocked_quarter:
                model.addConstr(x[product][quarter] == 0)
            else:
                model.addConstr(x[product][quarter] >= 0)
    
    for quarter in [1, 2, 3, 4]:
        model.addConstr(inventory["I"][quarter]["Iv_I_1"] == orders["I"][quarter] - x["I"][quarter] + inventory["I"][quarter - 1]["Iv_I_1"] if quarter != 1 else inventory["I"][quarter]["Iv_I_1"] == orders["I"][quarter] - x["I"][quarter])
        model.addConstr(inventory["II"][quarter]["Iv_II_1"] == orders["II"][quarter] - x["II"][quarter] + inventory["II"][quarter - 1]["Iv_II_1"] if quarter != 1 else inventory["II"][quarter]["Iv_II_1"] == orders["II"][quarter] - x["II"][quarter])
        model.addConstr(inventory["III"][quarter]["Iv_III_1"] == orders["III"][quarter] - x["III"][quarter] + inventory["III"][quarter - 1]["Iv_III_1"] if quarter != 1 else inventory["III"][quarter]["Iv_III_1"] == orders["III"][quarter] - x["III"][quarter])
    
    for quarter in [1, 2, 3, 4]:
        model.addConstr(inventory["I"][quarter]["Iv_I_2"] == inventory["I"][quarter - 1]["Iv_I_1"] - orders["I"][quarter] + x["I"][quarter])
        model.addConstr(inventory["II"][quarter]["Iv_II_2"] == inventory["II"][quarter - 1]["Iv_II_1"] - orders["II"][quarter] + x["II"][quarter])
        model.addConstr(inventory["III"][quarter]["Iv_III_2"] == inventory["III"][quarter - 1]["Iv_III_1"] - orders["III"][quarter] + x["III"][quarter])
    
    for quarter in [1, 2, 3, 4]:
        model.addConstr(inventory["I"][quarter]["Iv_I_3"] == inventory["I"][quarter - 1]["Iv_I_2"] - orders["I"][quarter] + x["I"][quarter])
        model.addConstr(inventory["II"][quarter]["Iv_II_3"] == inventory["II"][quarter - 1]["Iv_II_2"] - orders["II"][quarter] + x["II"][quarter])
        model.addConstr(inventory["III"][quarter]["Iv_III_3"] == inventory["III"][quarter - 1]["Iv_III_2"] - orders["III"][quarter] + x["III"][quarter])
    
    for quarter in [1, 2, 3, 4]:
        model.addConstr(inventory["I"][quarter]["Iv_I_4"] == inventory["I"][quarter - 1]["Iv_I_3"] - orders["I"][quarter] + x["I"][quarter])
        model.addConstr(inventory["II"][quarter]["Iv_II_4"] == inventory["II"][quarter - 1]["Iv_II_3"] - orders["II"][quarter] + x["II"][quarter])
        model.addConstr(inventory["III"][quarter]["Iv_III_4"] == inventory["III"][quarter - 1]["Iv_III_3"] - orders["III"][quarter] + x["III"][quarter])
    
    for quarter in [1, 2, 3, 4]:
        model.addConstr(inventory["I"][quarter]["Iv_I_4"] >= 150)
    
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            model.addConstr(late_penalty[product][quarter] >= orders[product][quarter] - inventory[product][quarter]["Iv_I_4"])
            model.addConstr(storage_cost[product][quarter] >= x[product][quarter] - orders[product][quarter])
    
    for product in ["I", "II"]:
        for quarter in [1, 2, 3, 4]:
            model.addConstr(late_penalty[product][quarter] * data["late_penalty_per_unit_per_quarter"][product] >= 0)
    
    for product in ["III"]:
        for quarter in [1, 2, 3, 4]:
            model.addConstr(late_penalty[product][quarter] * data["late_penalty_per_unit_per_quarter"][product] >= 0)
    
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            model.addConstr(storage_cost[product][quarter] * data["storage_cost_per_unit_per_quarter"] >= 0)
    
    # Objective function: Minimize total late-penalty and storage cost
    objective_function = 0
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            objective_function += late_penalty[product][quarter] * data["late_penalty_per_unit_per_quarter"][product] + storage_cost[product][quarter] * data["storage_cost_per_unit_per_quarter"]
    
    model.setObjective(objective_function, GRB.MINIMIZE)
    
    return model, {
        "x_I_1": x["I"][1],
        "x_I_2": x["I"][2],
        "x_I_3": x["I"][3],
        "x_I_4": x["I"][4],
        "x_II_1": x["II"][1],
        "x_II_2": x["II"][2],
        "x_II_3": x["II"][3],
        "x_II_4": x["II"][4],
        "x_III_1": x["III"][1],
        "x_III_2": x["III"][2],
        "x_III_3": x["III"][3],
        "x_III_4": x["III"][4],
        "Iv_I_1": inventory["I"][1]["Iv_I_1"],
        "Iv_I_2": inventory["I"][2]["Iv_I_2"],
        "Iv_I_3": inventory["I"][3]["Iv_I_3"],
        "Iv_I_4": inventory["I"][4]["Iv_I_4"],
        "Iv_II_1": inventory["II"][1]["Iv_II_1"],
        "Iv_II_2": inventory["II"][2]["Iv_II_2"],
        "Iv_II_3": inventory["II"][3]["Iv_II_3"],
        "Iv_II_4": inventory["II"][4]["Iv_II_4"],
        "Iv_III_1": inventory["III"][1]["Iv_III_1"],
        "Iv_III_2": inventory["III"][2]["Iv_III_2"],
        "Iv_III_3": inventory["III"][3]["Iv_III_3"],
        "Iv_III_4": inventory["III"][4]["Iv_III_4"],
        "Bk_I_1": backlog["I"][1]["Bk_I_1"],
        "Bk_I_2": backlog["I"][2]["Bk_I_2"],
        "Bk_I_3": backlog["I"][3]["Bk_I_3"],
        "Bk_I_4": backlog["I"][4]["Bk_I_4"],
        "Bk_II_1": backlog["II"][1]["Bk_II_1"],
        "Bk_II_2": backlog["II"][2]["Bk_II_2"],
        "Bk_II_3": backlog["II"][3]["Bk_II_3"],
        "Bk_II_4": backlog["II"][4]["Bk_II_4"],
        "Bk_III_1": backlog["III"][1]["Bk_III_1"],
        "Bk_III_2": backlog["III"][2]["Bk_III_2"],
        "Bk_III_3": backlog["III"][3]["Bk_III_3"],
        "Bk_III_4": backlog["III"][4]["Bk_III_4"]
    }

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "x_I_1": variables["x_I_1"].x,
                "x_I_2": variables["x_I_2"].x,
                "x_I_3": variables["x_I_3"].x,
                "x_I_4": variables["x_I_4"].x,
                "x_II_1": variables["x_II_1"].x,
                "x_II_2": variables["x_II_2"].x,
                "x_II_3": variables["x_II_3"].x,
                "x_II_4": variables["x_II_4"].x,
                "x_III_1": variables["x_III_1"].x,
                "x_III_2": variables["x_III_2"].x,
                "x_III_3": variables["x_III_3"].x,
                "x_III_4": variables["x_III_4"].x,
                "Iv_I_1": variables["Iv_I_1"].x,
                "Iv_I_2": variables["Iv_I_2"].x,
                "Iv_I_3": variables["Iv_I_3"].x,
                "Iv_I_4": variables["Iv_I_4"].x,
                "Iv_II_1": variables["Iv_II_1"].x,
                "Iv_II_2": variables["Iv_II_2"].x,
                "Iv_II_3": variables["Iv_II_3"].x,
                "Iv_II_4": variables["Iv_II_4"].x,
                "Iv_III_1": variables["Iv_III_1"].x,
                "Iv_III_2": variables["Iv_III_2"].x,
                "Iv_III_3": variables["Iv_III_3"].x,
                "Iv_III_4": variables["Iv_III_4"].x,
                "Bk_I_1": variables["Bk_I_1"].x,
                "Bk_I_2": variables["Bk_I_2"].x,
                "Bk_I_3": variables["Bk_I_3"].x,
                "Bk_I_4": variables["Bk_I_4"].x,
                "Bk_II_1": variables["Bk_II_1"].x,
                "Bk_II_2": variables["Bk_II_2"].x,
                "Bk_II_3": variables["Bk_II_3"].x,
                "Bk_II_4": variables["Bk_II_4"].x,
                "Bk_III_1": variables["Bk_III_1"].x,
                "Bk_III_2": variables["Bk_III_2"].x,
                "Bk_III_3": variables["Bk_III_3"].x,
                "Bk_III_4": variables["Bk_III_4"].x
            }
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {
                "x_I_1": None,
                "x_I_2": None,
                "x_I_3": None,
                "x_I_4": None,
                "x_II_1": None,
                "x_II_2": None,
                "x_II_3": None,
                "x_II_4": None,
                "x_III_1": None,
                "x_III_2": None,
                "x_III_3": None,
                "x_III_4": None,
                "Iv_I_1": None,
                "Iv_I_2": None,
                "Iv_I_3": None,
                "Iv_I_4": None,
                "Iv_II_1": None,
                "Iv_II_2": None,
                "Iv_II_3": None,
                "Iv_II_4": None,
                "Iv_III_1": None,
                "Iv_III_2": None,
                "Iv_III_3": None,
                "Iv_III_4": None,
                "Bk_I_1": None,
                "Bk_I_2": None,
                "Bk_I_3": None,
                "Bk_I_4": None,
                "Bk_II_1": None,
                "Bk_II_2": None,
                "Bk_II_3": None,
                "Bk_II_4": None,
                "Bk_III_1": None,
                "Bk_III_2": None,
                "Bk_III_3": None,
                "Bk_III_4": None
            }
        }