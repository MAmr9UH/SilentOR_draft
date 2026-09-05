import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("dyeing_plant_schedule")
    
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
        "y_1_1": model.addVar(name="y_1_1", vtype=GRB.BINARY),
        "y_1_2": model.addVar(name="y_1_2", vtype=GRB.BINARY),
        "y_1_3": model.addVar(name="y_1_3", vtype=GRB.BINARY),
        "y_1_4": model.addVar(name="y_1_4", vtype=GRB.BINARY),
        "y_1_5": model.addVar(name="y_1_5", vtype=GRB.BINARY),
        "y_2_1": model.addVar(name="y_2_1", vtype=GRB.BINARY),
        "y_2_2": model.addVar(name="y_2_2", vtype=GRB.BINARY),
        "y_2_3": model.addVar(name="y_2_3", vtype=GRB.BINARY),
        "y_2_4": model.addVar(name="y_2_4", vtype=GRB.BINARY),
        "y_2_5": model.addVar(name="y_2_5", vtype=GRB.BINARY),
        "y_3_1": model.addVar(name="y_3_1", vtype=GRB.BINARY),
        "y_3_2": model.addVar(name="y_3_2", vtype=GRB.BINARY),
        "y_3_3": model.addVar(name="y_3_3", vtype=GRB.BINARY),
        "y_3_4": model.addVar(name="y_3_4", vtype=GRB.BINARY),
        "y_3_5": model.addVar(name="y_3_5", vtype=GRB.BINARY),
        "y_4_1": model.addVar(name="y_4_1", vtype=GRB.BINARY),
        "y_4_2": model.addVar(name="y_4_2", vtype=GRB.BINARY),
        "y_4_3": model.addVar(name="y_4_3", vtype=GRB.BINARY),
        "y_4_4": model.addVar(name="y_4_4", vtype=GRB.BINARY),
        "y_4_5": model.addVar(name="y_4_5", vtype=GRB.BINARY),
        "y_5_1": model.addVar(name="y_5_1", vtype=GRB.BINARY),
        "y_5_2": model.addVar(name="y_5_2", vtype=GRB.BINARY),
        "y_5_3": model.addVar(name="y_5_3", vtype=GRB.BINARY),
        "y_5_4": model.addVar(name="y_5_4", vtype=GRB.BINARY),
        "y_5_5": model.addVar(name="y_5_5", vtype=GRB.BINARY),
        "C_1_1": model.addVar(name="C_1_1"),
        "C_1_2": model.addVar(name="C_1_2"),
        "C_1_3": model.addVar(name="C_1_3"),
        "C_2_1": model.addVar(name="C_2_1"),
        "C_2_2": model.addVar(name="C_2_2"),
        "C_2_3": model.addVar(name="C_2_3"),
        "C_3_1": model.addVar(name="C_3_1"),
        "C_3_2": model.addVar(name="C_3_2"),
        "C_3_3": model.addVar(name="C_3_3"),
        "C_4_1": model.addVar(name="C_4_1"),
        "C_4_2": model.addVar(name="C_4_2"),
        "C_4_3": model.addVar(name="C_4_3"),
        "C_5_1": model.addVar(name="C_5_1"),
        "C_5_2": model.addVar(name="C_5_2"),
        "C_5_3": model.addVar(name="C_5_3"),
        "Cmax": model.addVar(name="Cmax")
    }
    
    # Each batch is processed in exactly one position
    for batch in batches:
        model.addConstr(gp.quicksum(variables[f"y_{batch}_{position}"] for position in positions) == 1)
    
    # Define processing times
    for batch in batches:
        for position in positions:
            for vat in vats:
                if str(batch) in processing_time and str(vat) in processing_time[str(batch)]:
                    model.addConstr(variables[f"C_{batch}_{vat}"] >= processing_time[str(batch)][str(vat)] * variables[f"y_{batch}_{position}"])
    
    # Flow conservation
    for batch in batches:
        for position in positions[:-1]:
            for vat in vats:
                if batch < 5:
                    model.addConstr(variables[f"C_{batch}_{vat}"] <= variables[f"C_{batch + 1}_{vat}"])
    
    # Completion time of the last batch
    model.addConstr(variables["Cmax"] >= variables[f"C_{5}_{3}"])
    
    # Objective function: minimize the completion time of the last batch
    model.setObjective(variables["Cmax"], GRB.MINIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    
    if model.status == GRB.OPTIMAL:
        solution = {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": {
                "y_1_1": variables["y_1_1"].x,
                "y_1_2": variables["y_1_2"].x,
                "y_1_3": variables["y_1_3"].x,
                "y_1_4": variables["y_1_4"].x,
                "y_1_5": variables["y_1_5"].x,
                "y_2_1": variables["y_2_1"].x,
                "y_2_2": variables["y_2_2"].x,
                "y_2_3": variables["y_2_3"].x,
                "y_2_4": variables["y_2_4"].x,
                "y_2_5": variables["y_2_5"].x,
                "y_3_1": variables["y_3_1"].x,
                "y_3_2": variables["y_3_2"].x,
                "y_3_3": variables["y_3_3"].x,
                "y_3_4": variables["y_3_4"].x,
                "y_3_5": variables["y_3_5"].x,
                "y_4_1": variables["y_4_1"].x,
                "y_4_2": variables["y_4_2"].x,
                "y_4_3": variables["y_4_3"].x,
                "y_4_4": variables["y_4_4"].x,
                "y_4_5": variables["y_4_5"].x,
                "y_5_1": variables["y_5_1"].x,
                "y_5_2": variables["y_5_2"].x,
                "y_5_3": variables["y_5_3"].x,
                "y_5_4": variables["y_5_4"].x,
                "y_5_5": variables["y_5_5"].x,
                "C_1_1": variables["C_1_1"].x,
                "C_1_2": variables["C_1_2"].x,
                "C_1_3": variables["C_1_3"].x,
                "C_2_1": variables["C_2_1"].x,
                "C_2_2": variables["C_2_2"].x,
                "C_2_3": variables["C_2_3"].x,
                "C_3_1": variables["C_3_1"].x,
                "C_3_2": variables["C_3_2"].x,
                "C_3_3": variables["C_3_3"].x,
                "C_4_1": variables["C_4_1"].x,
                "C_4_2": variables["C_4_2"].x,
                "C_4_3": variables["C_4_3"].x,
                "C_5_1": variables["C_5_1"].x,
                "C_5_2": variables["C_5_2"].x,
                "C_5_3": variables["C_5_3"].x,
                "Cmax": variables["Cmax"].x
            }
        }
        return solution
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }