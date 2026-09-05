import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("dyeing_plant_schedule_model")
    
    batches = data["batches"]
    vats = data["vats"]
    positions = data["positions"]
    processing_time = data["processing_time"]
    
    variables_keys = {
        "y_1_1": "binary variable equal to 1 if batch 1 is placed in sequence position 1",
        "y_1_2": "binary variable equal to 1 if batch 1 is placed in sequence position 2",
        "y_1_3": "binary variable equal to 1 if batch 1 is placed in sequence position 3",
        "y_1_4": "binary variable equal to 1 if batch 1 is placed in sequence position 4",
        "y_1_5": "binary variable equal to 1 if batch 1 is placed in sequence position 5",
        "y_2_1": "binary variable equal to 1 if batch 2 is placed in sequence position 1",
        "y_2_2": "binary variable equal to 1 if batch 2 is placed in sequence position 2",
        "y_2_3": "binary variable equal to 1 if batch 2 is placed in sequence position 3",
        "y_2_4": "binary variable equal to 1 if batch 2 is placed in sequence position 4",
        "y_2_5": "binary variable equal to 1 if batch 2 is placed in sequence position 5",
        "y_3_1": "binary variable equal to 1 if batch 3 is placed in sequence position 1",
        "y_3_2": "binary variable equal to 1 if batch 3 is placed in sequence position 2",
        "y_3_3": "binary variable equal to 1 if batch 3 is placed in sequence position 3",
        "y_3_4": "binary variable equal to 1 if batch 3 is placed in sequence position 4",
        "y_3_5": "binary variable equal to 1 if batch 3 is placed in sequence position 5",
        "y_4_1": "binary variable equal to 1 if batch 4 is placed in sequence position 1",
        "y_4_2": "binary variable equal to 1 if batch 4 is placed in sequence position 2",
        "y_4_3": "binary variable equal to 1 if batch 4 is placed in sequence position 3",
        "y_4_4": "binary variable equal to 1 if batch 4 is placed in sequence position 4",
        "y_4_5": "binary variable equal to 1 if batch 4 is placed in sequence position 5",
        "y_5_1": "binary variable equal to 1 if batch 5 is placed in sequence position 1",
        "y_5_2": "binary variable equal to 1 if batch 5 is placed in sequence position 2",
        "y_5_3": "binary variable equal to 1 if batch 5 is placed in sequence position 3",
        "y_5_4": "binary variable equal to 1 if batch 5 is placed in sequence position 4",
        "y_5_5": "binary variable equal to 1 if batch 5 is placed in sequence position 5",
        "C_1_1": "completion time of sequence position 1 on vat 1",
        "C_1_2": "completion time of sequence position 1 on vat 2",
        "C_1_3": "completion time of sequence position 1 on vat 3",
        "C_2_1": "completion time of sequence position 2 on vat 1",
        "C_2_2": "completion time of sequence position 2 on vat 2",
        "C_2_3": "completion time of sequence position 2 on vat 3",
        "C_3_1": "completion time of sequence position 3 on vat 1",
        "C_3_2": "completion time of sequence position 3 on vat 2",
        "C_3_3": "completion time of sequence position 3 on vat 3",
        "C_4_1": "completion time of sequence position 4 on vat 1",
        "C_4_2": "completion time of sequence position 4 on vat 2",
        "C_4_3": "completion time of sequence position 4 on vat 3",
        "C_5_1": "completion time of sequence position 5 on vat 1",
        "C_5_2": "completion time of sequence position 5 on vat 2",
        "C_5_3": "completion time of sequence position 5 on vat 3",
        "Cmax": "makespan / completion time of the last batch"
    }
    
    variables = {
        "y": {
            (batch, position): model.addVar(name=f"y_{batch}_{position}", vtype=GRB.BINARY) for batch in batches for position in positions
        },
        "C": {
            (vat, position): model.addVar(name=f"C_{vat}_{position}", lb=0) for vat in vats for position in positions
        },
        "Cmax": model.addVar(name="Cmax", lb=0)
    }
    
    # Each batch is processed in exactly one position
    for batch in batches:
        model.addConstr(gp.quicksum(variables["y"][(batch, position)] for position in positions) == 1)
    
    # Define processing times
    for batch in batches:
        for vat in vats:
            for position in positions:
                if f"{batch}" in processing_time and str(vat) in processing_time[f"{batch}"]:
                    model.addConstr(variables["C"][(vat, position)] >= variables["C"][(vat, position - 1)] + processing_time[f"{batch}"][str(vat)] * variables["y"][(batch, position)] if position > 1 else variables["C"][(vat, position)] >= 0 * variables["y"][(batch, position)])
    
    # Objective function: minimize the completion time of the last batch
    model.setObjective(variables["C"][(3, 5)] + variables["C"][(2, 5)] + variables["C"][(1, 5)] + variables["C"][(4, 5)] + variables["C"][(5, 5)], GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "y_1_1": variables["y"][(1, 1)].x,
            "y_1_2": variables["y"][(1, 2)].x,
            "y_1_3": variables["y"][(1, 3)].x,
            "y_1_4": variables["y"][(1, 4)].x,
            "y_1_5": variables["y"][(1, 5)].x,
            "y_2_1": variables["y"][(2, 1)].x,
            "y_2_2": variables["y"][(2, 2)].x,
            "y_2_3": variables["y"][(2, 3)].x,
            "y_2_4": variables["y"][(2, 4)].x,
            "y_2_5": variables["y"][(2, 5)].x,
            "y_3_1": variables["y"][(3, 1)].x,
            "y_3_2": variables["y"][(3, 2)].x,
            "y_3_3": variables["y"][(3, 3)].x,
            "y_3_4": variables["y"][(3, 4)].x,
            "y_3_5": variables["y"][(3, 5)].x,
            "y_4_1": variables["y"][(4, 1)].x,
            "y_4_2": variables["y"][(4, 2)].x,
            "y_4_3": variables["y"][(4, 3)].x,
            "y_4_4": variables["y"][(4, 4)].x,
            "y_4_5": variables["y"][(4, 5)].x,
            "y_5_1": variables["y"][(5, 1)].x,
            "y_5_2": variables["y"][(5, 2)].x,
            "y_5_3": variables["y"][(5, 3)].x,
            "y_5_4": variables["y"][(5, 4)].x,
            "y_5_5": variables["y"][(5, 5)].x,
            "C_1_1": variables["C"][(1, 1)].x,
            "C_1_2": variables["C"][(1, 2)].x,
            "C_1_3": variables["C"][(1, 3)].x,
            "C_1_4": variables["C"][(1, 4)].x,
            "C_1_5": variables["C"][(1, 5)].x,
            "C_2_1": variables["C"][(2, 1)].x,
            "C_2_2": variables["C"][(2, 2)].x,
            "C_2_3": variables["C"][(2, 3)].x,
            "C_2_4": variables["C"][(2, 4)].x,
            "C_2_5": variables["C"][(2, 5)].x,
            "C_3_1": variables["C"][(3, 1)].x,
            "C_3_2": variables["C"][(3, 2)].x,
            "C_3_3": variables["C"][(3, 3)].x,
            "C_3_4": variables["C"][(3, 4)].x,
            "C_3_5": variables["C"][(3, 5)].x,
            "C_4_1": variables["C"][(4, 1)].x,
            "C_4_2": variables["C"][(4, 2)].x,
            "C_4_3": variables["C"][(4, 3)].x,
            "C_4_4": variables["C"][(4, 4)].x,
            "C_4_5": variables["C"][(4, 5)].x,
            "C_5_1": variables["C"][(5, 1)].x,
            "C_5_2": variables["C"][(5, 2)].x,
            "C_5_3": variables["C"][(5, 3)].x,
            "C_5_4": variables["C"][(5, 4)].x,
            "C_5_5": variables["C"][(5, 5)].x,
            "Cmax": model.objVal
        }
        return {
            "status": "OPTIMAL",
            "objective": solution["Cmax"],
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }