import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("recruitment_model")

    x = {}
    for type_id in data["types"]:
        for branch in data["branches"]:
            for specialty in data["specialties"]:
                x[f"x_{type_id}_{branch}_{specialty}"] = model.addVar(name=f"x_{type_id}_{branch}_{specialty}", lb=0, vtype=GRB.INTEGER)

    p3_shortfall = model.addVar(name="p3_shortfall", lb=0, vtype=GRB.INTEGER)

    # Demand constraints
    for branch in data["branches"]:
        for specialty in data["specialties"]:
            specialty_key = f"{branch}_{specialty}"
            model.addConstr(gp.quicksum(x[f"x_{type_id}_{branch}_{specialty}"] for type_id in data["types"] if specialty in data["suitable_specialties"].get(type_id, [])) >= data["demand"].get(specialty_key, 0))

    # P1: Fully meet all specialty demands
    # P2: Maximize the number of recruited personnel assigned to their preferred specialty
    # P3: Maximize the number assigned to their preferred city

    # P2 Objective: Maximize the number of people assigned to their preferred specialty
    model.setObjective(
        gp.quicksum(x[f"x_{type_id}_{branch}_{specialty}"] for type_id in data["types"] for branch in data["branches"] for specialty in data["specialties"] if specialty == data["preferred_specialty"].get(type_id, 0)),
        GRB.MAXIMIZE)

    # P3 Objective: Maximize the number of people assigned to their preferred city
    model.addConstr(
        gp.quicksum(x[f"x_{type_id}_{branch}_{specialty}"] for type_id in data["types"] for branch in data["branches"] for specialty in data["specialties"] if branch == data["preferred_city"].get(type_id, "default_branch")) <= data["p3_preferred_city_target"] + p3_shortfall)

    # Available people constraint
    for type_id in data["types"]:
        model.addConstr(gp.quicksum(x[f"x_{type_id}_{branch}_{specialty}"] for branch in data["branches"] for specialty in data["specialties"] if specialty in data["suitable_specialties"].get(type_id, [])) <= data["available_people"].get(str(type_id), 0))

    # P2 target
    model.addConstr(
        gp.quicksum(x[f"x_{type_id}_{branch}_{specialty}"] for type_id in data["types"] for branch in data["branches"] for specialty in data["specialties"] if specialty == data["preferred_specialty"].get(type_id, 0)) <= data["p2_preferred_specialty_target"])

    return model, x, p3_shortfall

def solve(data: dict) -> dict:
    model, x, p3_shortfall = build_model(data)
    model.optimize()

    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_Donghai_1": x["x_1_Donghai_1"].x,
            "x_1_Donghai_2": x["x_1_Donghai_2"].x,
            "x_1_Nanjiang_1": x["x_1_Nanjiang_1"].x,
            "x_1_Nanjiang_2": x["x_1_Nanjiang_2"].x,
            "x_2_Donghai_2": x["x_2_Donghai_2"].x,
            "x_2_Donghai_3": x["x_2_Donghai_3"].x,
            "x_2_Nanjiang_2": x["x_2_Nanjiang_2"].x,
            "x_2_Nanjiang_3": x["x_2_Nanjiang_3"].x,
            "x_3_Donghai_1": x["x_3_Donghai_1"].x,
            "x_3_Donghai_3": x["x_3_Donghai_3"].x,
            "x_3_Nanjiang_1": x["x_3_Nanjiang_1"].x,
            "x_3_Nanjiang_3": x["x_3_Nanjiang_3"].x,
            "x_4_Donghai_1": x["x_4_Donghai_1"].x,
            "x_4_Donghai_3": x["x_4_Donghai_3"].x,
            "x_4_Nanjiang_1": x["x_4_Nanjiang_1"].x,
            "x_4_Nanjiang_3": x["x_4_Nanjiang_3"].x,
            "x_5_Donghai_2": x["x_5_Donghai_2"].x,
            "x_5_Donghai_3": x["x_5_Donghai_3"].x,
            "x_5_Nanjiang_2": x["x_5_Nanjiang_2"].x,
            "x_5_Nanjiang_3": x["x_5_Nanjiang_3"].x,
            "x_6_Donghai_3": x["x_6_Donghai_3"].x,
            "x_6_Nanjiang_3": x["x_6_Nanjiang_3"].x,
            "p3_shortfall": p3_shortfall.x
        }
        return {
            "status": "OPTIMAL",
            "objective": solution["p3_shortfall"],
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }