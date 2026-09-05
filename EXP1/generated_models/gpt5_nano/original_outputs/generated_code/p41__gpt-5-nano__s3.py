import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    # Optional: suppress solver output
    model.Params.OutputFlag = 0

    # Decision variables (flat continuous)
    produce_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_liquid")
    produce_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="produce_solid")
    ending_liquid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_liquid")
    ending_solid = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="ending_solid")

    model.update()

    init_liquid = data["initial_inventory"]["liquid"]
    init_solid = data["initial_inventory"]["solid"]
    demand_liquid = data["demand"]["liquid"]
    demand_solid = data["demand"]["solid"]

    avail_machine1 = data["available_hours"]["machine1"] * 60  # convert hours to minutes
    avail_machine2 = data["available_hours"]["machine2"] * 60

    # Time constraints on machines
    model.addConstr(50 * produce_liquid + 24 * produce_solid <= avail_machine1, name="Machine1_Time")
    model.addConstr(30 * produce_liquid + 33 * produce_solid <= avail_machine2, name="Machine2_Time")

    # Ending inventory balances
    model.addConstr(ending_liquid == init_liquid + produce_liquid - demand_liquid, name="EndingLiquidBalance")
    model.addConstr(ending_solid  == init_solid  + produce_solid  - demand_solid,  name="EndingSolidBalance")

    # Objective: maximize total ending inventory
    model.setObjective(ending_liquid + ending_solid, GRB.MAXIMIZE)

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

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    solution = {
        "produce_liquid": variables["produce_liquid"].X,
        "produce_solid": variables["produce_solid"].X,
        "ending_liquid": variables["ending_liquid"].X,
        "ending_solid": variables["ending_solid"].X
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }