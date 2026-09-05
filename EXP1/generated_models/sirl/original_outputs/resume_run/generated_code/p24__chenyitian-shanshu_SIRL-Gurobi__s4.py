import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("container_packing_model")
    
    # Decision variables
    y = {}
    uA = {}
    q = {}

    for i in range(1, 11):
        y[i] = model.addVar(name=f"y_{i}", vtype=GRB.BINARY)
        uA[i] = model.addVar(name=f"uA_{i}", vtype=GRB.BINARY)
        for good in ["A", "B", "C", "D", "E"]:
            q[i, good] = model.addVar(name=f"q_{i}_{good}", vtype=GRB.INTEGER)

    # Objective function: Minimize the number of containers used
    model.setObjective(gp.quicksum(y[i] for i in range(1, 11)), GRB.MINIMIZE)

    # Container capacity constraint
    for i in range(1, 11):
        model.addConstr(
            0.5 * q[i, "A"] + 1.0 * q[i, "B"] + 0.4 * q[i, "C"] + 0.6 * q[i, "D"] + 0.65 * q[i, "E"] <= 60 * y[i]
        )

    # Each used container must load at least 18 tons
    for i in range(1, 11):
        model.addConstr(
            0.5 * q[i, "A"] + 1.0 * q[i, "B"] + 0.4 * q[i, "C"] + 0.6 * q[i, "D"] + 0.65 * q[i, "E"] >= 18 * y[i]
        )

    # Each used container must load at least 12 units of D
    for i in range(1, 11):
        model.addConstr(q[i, "D"] >= 12 * y[i])

    # If any A is loaded, at least one C must be loaded
    for i in range(1, 11):
        model.addConstr(q[i, "A"] <= 1000 * uA[i])
        model.addConstr(q[i, "C"] >= q[i, "A"])

    # Total quantity of each good
    total_quantity = {
        "A": 120,
        "B": 90,
        "C": 300,
        "D": 90,
        "E": 120
    }

    for good in ["A", "B", "C", "D", "E"]:
        model.addConstr(gp.quicksum(q[i, good] for i in range(1, 11)) == total_quantity[good])

    return model, {
        "y_1": y[1],
        "y_2": y[2],
        "y_3": y[3],
        "y_4": y[4],
        "y_5": y[5],
        "y_6": y[6],
        "y_7": y[7],
        "y_8": y[8],
        "y_9": y[9],
        "y_10": y[10],
        "uA_1": uA[1],
        "uA_2": uA[2],
        "uA_3": uA[3],
        "uA_4": uA[4],
        "uA_5": uA[5],
        "uA_6": uA[6],
        "uA_7": uA[7],
        "uA_8": uA[8],
        "uA_9": uA[9],
        "uA_10": uA[10],
        "q_1_A": q[1, "A"],
        "q_1_B": q[1, "B"],
        "q_1_C": q[1, "C"],
        "q_1_D": q[1, "D"],
        "q_1_E": q[1, "E"],
        "q_2_A": q[2, "A"],
        "q_2_B": q[2, "B"],
        "q_2_C": q[2, "C"],
        "q_2_D": q[2, "D"],
        "q_2_E": q[2, "E"],
        "q_3_A": q[3, "A"],
        "q_3_B": q[3, "B"],
        "q_3_C": q[3, "C"],
        "q_3_D": q[3, "D"],
        "q_3_E": q[3, "E"],
        "q_4_A": q[4, "A"],
        "q_4_B": q[4, "B"],
        "q_4_C": q[4, "C"],
        "q_4_D": q[4, "D"],
        "q_4_E": q[4, "E"],
        "q_5_A": q[5, "A"],
        "q_5_B": q[5, "B"],
        "q_5_C": q[5, "C"],
        "q_5_D": q[5, "D"],
        "q_5_E": q[5, "E"],
        "q_6_A": q[6, "A"],
        "q_6_B": q[6, "B"],
        "q_6_C": q[6, "C"],
        "q_6_D": q[6, "D"],
        "q_6_E": q[6, "E"],
        "q_7_A": q[7, "A"],
        "q_7_B": q[7, "B"],
        "q_7_C": q[7, "C"],
        "q_7_D": q[7, "D"],
        "q_7_E": q[7, "E"],
        "q_8_A": q[8, "A"],
        "q_8_B": q[8, "B"],
        "q_8_C": q[8, "C"],
        "q_8_D": q[8, "D"],
        "q_8_E": q[8, "E"],
        "q_9_A": q[9, "A"],
        "q_9_B": q[9, "B"],
        "q_9_C": q[9, "C"],
        "q_9_D": q[9, "D"],
        "q_9_E": q[9, "E"],
        "q_10_A": q[10, "A"],
        "q_10_B": q[10, "B"],
        "q_10_C": q[10, "C"],
        "q_10_D": q[10, "D"],
        "q_10_E": q[10, "E"]
    }

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "y_1": variables["y_1"].x,
                "y_2": variables["y_2"].x,
                "y_3": variables["y_3"].x,
                "y_4": variables["y_4"].x,
                "y_5": variables["y_5"].x,
                "y_6": variables["y_6"].x,
                "y_7": variables["y_7"].x,
                "y_8": variables["y_8"].x,
                "y_9": variables["y_9"].x,
                "y_10": variables["y_10"].x,
                "uA_1": variables["uA_1"].x,
                "uA_2": variables["uA_2"].x,
                "uA_3": variables["uA_3"].x,
                "uA_4": variables["uA_4"].x,
                "uA_5": variables["uA_5"].x,
                "uA_6": variables["uA_6"].x,
                "uA_7": variables["uA_7"].x,
                "uA_8": variables["uA_8"].x,
                "uA_9": variables["uA_9"].x,
                "uA_10": variables["uA_10"].x,
                "q_1_A": variables["q_1_A"].x,
                "q_1_B": variables["q_1_B"].x,
                "q_1_C": variables["q_1_C"].x,
                "q_1_D": variables["q_1_D"].x,
                "q_1_E": variables["q_1_E"].x,
                "q_2_A": variables["q_2_A"].x,
                "q_2_B": variables["q_2_B"].x,
                "q_2_C": variables["q_2_C"].x,
                "q_2_D": variables["q_2_D"].x,
                "q_2_E": variables["q_2_E"].x,
                "q_3_A": variables["q_3_A"].x,
                "q_3_B": variables["q_3_B"].x,
                "q_3_C": variables["q_3_C"].x,
                "q_3_D": variables["q_3_D"].x,
                "q_3_E": variables["q_3_E"].x,
                "q_4_A": variables["q_4_A"].x,
                "q_4_B": variables["q_4_B"].x,
                "q_4_C": variables["q_4_C"].x,
                "q_4_D": variables["q_4_D"].x,
                "q_4_E": variables["q_4_E"].x,
                "q_5_A": variables["q_5_A"].x,
                "q_5_B": variables["q_5_B"].x,
                "q_5_C": variables["q_5_C"].x,
                "q_5_D": variables["q_5_D"].x,
                "q_5_E": variables["q_5_E"].x,
                "q_6_A": variables["q_6_A"].x,
                "q_6_B": variables["q_6_B"].x,
                "q_6_C": variables["q_6_C"].x,
                "q_6_D": variables["q_6_D"].x,
                "q_6_E": variables["q_6_E"].x,
                "q_7_A": variables["q_7_A"].x,
                "q_7_B": variables["q_7_B"].x,
                "q_7_C": variables["q_7_C"].x,
                "q_7_D": variables["q_7_D"].x,
                "q_7_E": variables["q_7_E"].x,
                "q_8_A": variables["q_8_A"].x,
                "q_8_B": variables["q_8_B"].x,
                "q_8_C": variables["q_8_C"].x,
                "q_8_D": variables["q_8_D"].x,
                "q_8_E": variables["q_8_E"].x,
                "q_9_A": variables["q_9_A"].x,
                "q_9_B": variables["q_9_B"].x,
                "q_9_C": variables["q_9_C"].x,
                "q_9_D": variables["q_9_D"].x,
                "q_9_E": variables["q_9_E"].x,
                "q_10_A": variables["q_10_A"].x,
                "q_10_B": variables["q_10_B"].x,
                "q_10_C": variables["q_10_C"].x,
                "q_10_D": variables["q_10_D"].x,
                "q_10_E": variables["q_10_E"].x
            }
        }
        return solution
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }