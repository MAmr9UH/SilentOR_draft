import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    produce_liquid = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    produce_solid = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    ending_liquid = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    ending_solid = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)

    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    model.addConstr(50 * produce_liquid + 24 * produce_solid <= data["available_hours"]["machine1"] * 60)
    model.addConstr(30 * produce_liquid + 33 * produce_solid <= data["available_hours"]["machine2"] * 60)

    model.addConstr(ending_liquid == data["initial_inventory"]["liquid"] + produce_liquid - data["demand"]["liquid"])
    model.addConstr(ending_solid == data["initial_inventory"]["solid"] + produce_solid - data["demand"]["solid"])

    model.setObjective(ending_liquid + ending_solid, gp.GRB.MAXIMIZE)

    return model, variables


def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {
        "produce_liquid": model.getVarByName("produce_liquid").X,
        "produce_solid": model.getVarByName("produce_solid").X,
        "ending_liquid": model.getVarByName("ending_liquid").X,
        "ending_solid": model.getVarByName("ending_solid").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }