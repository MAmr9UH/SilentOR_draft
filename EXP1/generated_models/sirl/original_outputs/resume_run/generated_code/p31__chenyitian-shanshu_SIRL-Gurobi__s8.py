import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("recruitment_model")
    
    # Decision variables
    x = {}
    for type_id in data["types"]:
        for branch in data["branches"]:
            for specialty in data["specialties"]:
                x[type_id, branch, specialty] = model.addVar(name=f"x_{type_id}_{branch}_{specialty}", lb=0, vtype=GRB.INTEGER)
    
    p3_shortfall = model.addVar(name="p3_shortfall", lb=0, vtype=GRB.INTEGER)

    # Available people
    available_people = data["available_people"]

    # Suitable specialties
    suitable_specialties = data["suitable_specialties"]

    # Preferred specialty
    preferred_specialty = data["preferred_specialty"]

    # Preferred city
    preferred_city = data["preferred_city"]

    # Demand
    demand = data["demand"]

    # P2 target
    p2_target = data["p2_preferred_specialty_target"]

    # P3 target
    p3_target = data["p3_preferred_city_target"]

    # Objective function for P1: meet all specialty demands
    for branch in data["branches"]:
        for specialty in data["specialties"]:
            model.addConstr(gp.quicksum(x[type_id, branch, specialty] for type_id in data["types"] if specialty in suitable_specialties.get(type_id, [])) >= demand[f"{branch}_{specialty}"])

    # Objective function for P2: maximize the number of recruited personnel assigned to their preferred specialty
    p2_objective = 0
    for type_id in data["types"]:
        if preferred_specialty[type_id] in suitable_specialties.get(type_id, []):
            p2_objective += x[type_id, "Donghai", preferred_specialty[type_id]] + x[type_id, "Nanjiang", preferred_specialty[type_id]]
    
    model.addConstr(p2_objective <= p2_target)

    # Objective function for P3: maximize the number assigned to their preferred city
    p3_objective = 0
    for type_id in data["types"]:
        if preferred_city[type_id] == "Donghai":
            p3_objective += x[type_id, "Donghai", 1] + x[type_id, "Donghai", 2] + x[type_id, "Donghai", 3]
        else:
            p3_objective += x[type_id, "Nanjiang", 1] + x[type_id, "Nanjiang", 2] + x[type_id, "Nanjiang", 3]
    
    model.addConstr(p3_objective <= p3_target + p3_shortfall)

    # Number of people for each type
    for type_id in data["types"]:
        model.addConstr(gp.quicksum(x[type_id, branch, specialty] for branch in data["branches"] for specialty in data["specialties"] if specialty in suitable_specialties.get(type_id, [])) <= available_people[str(type_id)])

    # Solve the model
    return model, x, p3_shortfall

def solve(data: dict) -> dict:
    model, x, p3_shortfall = build_model(data)
    
    # Optimize the model
    model.optimize()

    # Check if the model is optimal
    if model.status == GRB.OPTIMAL:
        solution = {
            "x_1_Donghai_1": x[1, "Donghai", 1].x,
            "x_1_Donghai_2": x[1, "Donghai", 2].x,
            "x_1_Nanjiang_1": x[1, "Nanjiang", 1].x,
            "x_1_Nanjiang_2": x[1, "Nanjiang", 2].x,
            "x_2_Donghai_2": x[2, "Donghai", 2].x,
            "x_2_Donghai_3": x[2, "Donghai", 3].x,
            "x_2_Nanjiang_2": x[2, "Nanjiang", 2].x,
            "x_2_Nanjiang_3": x[2, "Nanjiang", 3].x,
            "x_3_Donghai_1": x[3, "Donghai", 1].x,
            "x_3_Donghai_3": x[3, "Donghai", 3].x,
            "x_3_Nanjiang_1": x[3, "Nanjiang", 1].x,
            "x_3_Nanjiang_3": x[3, "Nanjiang", 3].x,
            "x_4_Donghai_1": x[4, "Donghai", 1].x,
            "x_4_Donghai_3": x[4, "Donghai", 3].x,
            "x_4_Nanjiang_1": x[4, "Nanjiang", 1].x,
            "x_4_Nanjiang_3": x[4, "Nanjiang", 3].x,
            "x_5_Donghai_2": x[5, "Donghai", 2].x,
            "x_5_Donghai_3": x[5, "Donghai", 3].x,
            "x_5_Nanjiang_2": x[5, "Nanjiang", 2].x,
            "x_5_Nanjiang_3": x[5, "Nanjiang", 3].x,
            "x_6_Donghai_3": x[6, "Donghai", 3].x,
            "x_6_Nanjiang_3": x[6, "Nanjiang", 3].x,
            "p3_shortfall": p3_shortfall.x
        }
        return {
            "status": "OPTIMAL",
            "objective": p3_shortfall.x,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": {}
        }