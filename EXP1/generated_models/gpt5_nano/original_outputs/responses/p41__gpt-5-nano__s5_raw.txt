def build_model(data: dict):
    from gurobipy import Model, GRB

    # Extract data
    initial_liquid = data["initial_inventory"]["liquid"]
    initial_solid = data["initial_inventory"]["solid"]
    demand_liquid = data["demand"]["liquid"]
    demand_solid = data["demand"]["solid"]

    hours_machine1 = data["available_hours"]["machine1"]
    hours_machine2 = data["available_hours"]["machine2"]
    minutes_machine1 = hours_machine1 * 60
    minutes_machine2 = hours_machine2 * 60

    t1_liquid = data["machine_minutes"]["machine1"]["liquid"]
    t1_solid = data["machine_minutes"]["machine1"]["solid"]
    t2_liquid = data["machine_minutes"]["machine2"]["liquid"]
    t2_solid = data["machine_minutes"]["machine2"]["solid"]

    # Create model
    model = Model()

    # Decision variables
    produce_liquid = model.addVar(lb=0.0, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, name="ending_solid")

    model.update()

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)

    # Time constraints
    model.addConstr(t1_liquid * produce_liquid + t1_solid * produce_solid <= minutes_machine1, name="Machine1_minutes")
    model.addConstr(t2_liquid * produce_liquid + t2_solid * produce_solid <= minutes_machine2, name="Machine2_minutes")

    # Inventory balance equations
    model.addConstr(initial_liquid + produce_liquid - demand_liquid == ending_liquid, name="Balance_liquid")
    model.addConstr(initial_solid + produce_solid - demand_solid == ending_solid, name="Balance_solid")

    # Return model and variables
    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    return model, variables

def solve(data: dict) -> dict:
    from gurobipy import GRB

    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(status_code, str(status_code))

    # Ensure model is updated before reading variable values
    model.update()

    solution = {
        "produce_liquid": variables["produce_liquid"].X,
        "produce_solid": variables["produce_solid"].X,
        "ending_liquid": variables["ending_liquid"].X,
        "ending_solid": variables["ending_solid"].X
    }

    objective = model.ObjVal if model.ObjVal is not None else None

    return {
        "status": status,
        "objective": float(objective) if objective is not None else None,
        "solution": solution
    }