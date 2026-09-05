import gurobipy as gp

def build_model(data: dict):
    m = gp.Model()

    # Extract data
    initial_liq = data["initial_inventory"]["liquid"]
    initial_sol = data["initial_inventory"]["solid"]
    demand_liq = data["demand"]["liquid"]
    demand_sol = data["demand"]["solid"]

    m1_liq = data["machine_minutes"]["machine1"]["liquid"]
    m1_sol = data["machine_minutes"]["machine1"]["solid"]
    m2_liq = data["machine_minutes"]["machine2"]["liquid"]
    m2_sol = data["machine_minutes"]["machine2"]["solid"]

    hours_m1 = data["available_hours"]["machine1"]
    hours_m2 = data["available_hours"]["machine2"]

    cap_m1 = hours_m1 * 60.0
    cap_m2 = hours_m2 * 60.0

    # Decision variables (continuous, non-negative)
    produce_liquid = m.addVar(lb=0.0, name="produce_liquid")
    produce_solid = m.addVar(lb=0.0, name="produce_solid")
    ending_liquid = m.addVar(lb=0.0, name="ending_liquid")
    ending_solid = m.addVar(lb=0.0, name="ending_solid")

    m.update()

    # Time constraints
    m.addConstr(m1_liq * produce_liquid + m1_sol * produce_solid <= cap_m1, name="mach1_time")
    m.addConstr(m2_liq * produce_liquid + m2_sol * produce_solid <= cap_m2, name="mach2_time")

    # Inventory balance equations
    m.addConstr(ending_liquid == initial_liq + produce_liquid - demand_liq, name="bal_liq")
    m.addConstr(ending_solid == initial_sol + produce_solid - demand_sol, name="bal_sol")

    # Objective: maximize total ending inventory
    m.setObjective(ending_liquid + ending_solid, sense=gp.GRB.MAXIMIZE)

    variables = {
        "produce_liquid": produce_liquid,
        "produce_solid": produce_solid,
        "ending_liquid": ending_liquid,
        "ending_solid": ending_solid
    }

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status = status_map.get(model.Status, str(model.Status))

    objective = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {
        "produce_liquid": None,
        "produce_solid": None,
        "ending_liquid": None,
        "ending_solid": None
    }

    if model.Status == gp.GRB.OPTIMAL:
        solution["produce_liquid"] = float(variables["produce_liquid"].X)
        solution["produce_solid"] = float(variables["produce_solid"].X)
        solution["ending_liquid"] = float(variables["ending_liquid"].X)
        solution["ending_solid"] = float(variables["ending_solid"].X)

    return {
        "status": status,
        "objective": objective,
        "solution": solution
    }