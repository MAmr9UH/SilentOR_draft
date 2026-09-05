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
    
    # Model constraints
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            # Production capacity constraint
            model.addConstr(gp.quicksum(hours_per_unit[p] * x[product][quarter] for p in ["I", "II", "III"]) <= capacity_hours_per_quarter)
            
            # Ending inventory
            if quarter == 1:
                model.addConstr(inventory[product][quarter] == x[product][quarter] - orders[product][quarter] + inventory[product][quarter])
            else:
                model.addConstr(inventory[product][quarter] == x[product][quarter] - orders[product][quarter] + inventory[product][quarter - 1])
            
            # Backlog
            model.addConstr(orders[product][quarter] - x[product][quarter] - inventory[product][quarter] <= backlog[product][quarter])
            
            # Late penalty
            model.addConstr(late_penalty[product][quarter] >= backlog[product][quarter] * late_penalty_per_unit_per_quarter[product])
            
            # Storage cost
            model.addConstr(storage_cost[product][quarter] >= inventory[product][quarter] * storage_cost_per_unit_per_quarter)
    
    # Product I cannot be produced in quarter 2
    model.addConstr(x["I"][2] == 0)
    
    # Ending inventory requirement
    model.addConstr(inventory["I"][4] == 150)
    model.addConstr(inventory["II"][4] == 150)
    model.addConstr(inventory["III"][4] == 150)
    
    # Objective function: Minimize total late-penalty and storage cost
    objective_function = 0
    for product in ["I", "II", "III"]:
        for quarter in [1, 2, 3, 4]:
            objective_function += late_penalty[product][quarter] + storage_cost[product][quarter]
    
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
        "Iv_I_1": inventory["I"][1],
        "Iv_I_2": inventory["I"][2],
        "Iv_I_3": inventory["I"][3],
        "Iv_I_4": inventory["I"][4],
        "Iv_II_1": inventory["II"][1],
        "Iv_II_2": inventory["II"][2],
        "Iv_II_3": inventory["II"][3],
        "Iv_II_4": inventory["II"][4],
        "Iv_III_1": inventory["III"][1],
        "Iv_III_2": inventory["III"][2],
        "Iv_III_3": inventory["III"][3],
        "Iv_III_4": inventory["III"][4],
        "Bk_I_1": backlog["I"][1],
        "Bk_I_2": backlog["I"][2],
        "Bk_I_3": backlog["I"][3],
        "Bk_I_4": backlog["I"][4],
        "Bk_II_1": backlog["II"][1],
        "Bk_II_2": backlog["II"][2],
        "Bk_II_3": backlog["II"][3],
        "Bk_II_4": backlog["II"][4],
        "Bk_III_1": backlog["III"][1],
        "Bk_III_2": backlog["III"][2],
        "Bk_III_3": backlog["III"][3],
        "Bk_III_4": backlog["III"][4],
        "late_penalty_I_1": late_penalty["I"][1],
        "late_penalty_I_2": late_penalty["I"][2],
        "late_penalty_I_3": late_penalty["I"][3],
        "late_penalty_I_4": late_penalty["I"][4],
        "late_penalty_II_1": late_penalty["II"][1],
        "late_penalty_II_2": late_penalty["II"][2],
        "late_penalty_II_3": late_penalty["II"][3],
        "late_penalty_II_4": late_penalty["II"][4],
        "late_penalty_III_1": late_penalty["III"][1],
        "late_penalty_III_2": late_penalty["III"][2],
        "late_penalty_III_3": late_penalty["III"][3],
        "late_penalty_III_4": late_penalty["III"][4],
        "storage_cost_I_1": storage_cost["I"][1],
        "storage_cost_I_2": storage_cost["I"][2],
        "storage_cost_I_3": storage_cost["I"][3],
        "storage_cost_I_4": storage_cost["I"][4],
        "storage_cost_II_1": storage_cost["II"][1],
        "storage_cost_II_2": storage_cost["II"][2],
        "storage_cost_II_3": storage_cost["II"][3],
        "storage_cost_II_4": storage_cost["II"][4],
        "storage_cost_III_1": storage_cost["III"][1],
        "storage_cost_III_2": storage_cost["III"][2],
        "storage_cost_III_3": storage_cost["III"][3],
        "storage_cost_III_4": storage_cost["III"][4]
    }

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
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
        return solution
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }