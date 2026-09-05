import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    durations = data["durations"]
    activities = data["activities"]

    # Decision variables: start times for each activity
    start = {}
    for a in activities:
        start[a] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"start_{a}")

    # Makespan and machine span
    Cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Cmax")
    machine_span = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="machine_span")

    model.update()

    # Precedence constraints: end(p) <= start(succ)
    for (p, succ) in data["precedence"]:
        model.addConstr(start[p] + durations[p] <= start[succ], name=f"prec_{p}_{succ}")

    # Makespan: Cmax >= end_i for all i
    for a in activities:
        model.addConstr(Cmax >= start[a] + durations[a], name=f"cmax_{a}")

    # Machine rental span constraint: machine_span = end_B - start_A
    model.addConstr(machine_span == (start["B"] + durations["B"]) - start["A"], name="machine_span_def")

    # Objective: minimize total cost = work_cost * Cmax + machine_cost * machine_span
    work_cost = data["work_cost_per_project_day"]
    machine_cost = data["machine_rental_cost_per_day"]
    model.setObjective(work_cost * Cmax + machine_cost * machine_span, GRB.MINIMIZE)

    variables = {
        "start_A": start["A"],
        "start_B": start["B"],
        "start_C": start["C"],
        "start_D": start["D"],
        "start_E": start["E"],
        "start_F": start["F"],
        "start_G": start["G"],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    stat = model.Status
    if stat == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif stat == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif stat == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif stat == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif stat == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(stat)

    model.update()
    objective = float(model.ObjVal)

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
        "objective": objective,
        "solution": solution
    }