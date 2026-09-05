import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Decision variables
    produce_liquid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=gp.GRB.CONTINUOUS, name="ending_solid")

    # Parameters from data
    machine1 = data["machine_minutes"]["machine1"]
    machine2 = data["machine_minutes"]["machine2"]
    available_hours = data["available_hours"]

    initial_inventory = data["initial_inventory"]
    demand = data["demand"]

    # Capacity constraints
    model.addConstr(machine1["liquid"] * produce_liquid + machine1["solid"] * produce_solid <=
                    available_hours["machine1"] * 60)
    model.addConstr(machine2["liquid"] * produce_liquid + machine2["solid"] * produce_solid <=
                    available_hours["machine2"] * 60)

    # Linking ending inventory
    model.addConstr(ending_liquid == initial_inventory["liquid"] + produce_liquid - demand["liquid"])
    model.addConstr(ending_solid == initial_inventory["solid"] + produce_solid - demand["solid"])

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, gp.GRB.MAXIMIZE)

    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    import gurobipy as gp

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(model.Status, str(model.Status))

    model.update()
    solution = {
        "produce_liquid": float(variables["produce_liquid"].X),
        "produce_solid": float(variables["produce_solid"].X),
        "ending_liquid": float(variables["ending_liquid"].X),
        "ending_solid": float(variables["ending_solid"].X)
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }