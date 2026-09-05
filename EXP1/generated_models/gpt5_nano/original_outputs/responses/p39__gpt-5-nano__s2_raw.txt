import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    durations = data["durations"]
    activities = data["activities"]

    # Decision variables: start times for each activity
    start_vars = {}
    for a in activities:
        start_vars[a] = model.addVar(lb=0.0, name=f"start_{a}", vtype=GRB.CONTINUOUS)

    # Makespan and machine span
    Cmax = model.addVar(lb=0.0, name="Cmax", vtype=GRB.CONTINUOUS)
    machine_span = model.addVar(lb=0.0, name="machine_span", vtype=GRB.CONTINUOUS)

    model.update()

    # Non-negativity (implicit by lb=0, but explicit for clarity)
    for a in activities:
        model.addConstr(start_vars[a] >= 0)

    # Precedence constraints
    model.addConstr(start_vars['G'] >= start_vars['A'] + durations['A'])
    model.addConstr(start_vars['D'] >= start_vars['A'] + durations['A'])
    model.addConstr(start_vars['F'] >= start_vars['E'] + durations['E'])
    model.addConstr(start_vars['F'] >= start_vars['G'] + durations['G'])
    model.addConstr(start_vars['C'] >= start_vars['D'] + durations['D'])
    model.addConstr(start_vars['C'] >= start_vars['F'] + durations['F'])
    model.addConstr(start_vars['B'] >= start_vars['F'] + durations['F'])

    # Cmax constraints: Cmax must be at least completion time of every activity
    for a in activities:
        model.addConstr(Cmax >= start_vars[a] + durations[a])

    # Machine span definition: end_B - start_A
    model.addConstr(machine_span == (start_vars['B'] + durations['B']) - start_vars['A'])

    # Objective: minimize total cost
    work_cost = data["work_cost_per_project_day"]
    machine_cost = data["machine_rental_cost_per_day"]
    model.setObjective(work_cost * Cmax + machine_cost * machine_span, GRB.MINIMIZE)

    variables = {
        "start_A": start_vars['A'],
        "start_B": start_vars['B'],
        "start_C": start_vars['C'],
        "start_D": start_vars['D'],
        "start_E": start_vars['E'],
        "start_F": start_vars['F'],
        "start_G": start_vars['G'],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()
    model.update()

    status_val = model.Status
    status_str = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }.get(status_val, str(status_val))

    objective = model.ObjVal

    solution = {
        "start_A": float(variables["start_A"].X),
        "start_B": float(variables["start_B"].X),
        "start_C": float(variables["start_C"].X),
        "start_D": float(variables["start_D"].X),
        "start_E": float(variables["start_E"].X),
        "start_F": float(variables["start_F"].X),
        "start_G": float(variables["start_G"].X),
        "Cmax": float(variables["Cmax"].X),
        "machine_span": float(variables["machine_span"].X)
    }

    return {
        "status": status_str,
        "objective": float(objective),
        "solution": solution
    }