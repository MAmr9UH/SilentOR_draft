import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()

    activities = data["activities"]
    dur = data["durations"]

    # Decision variables: start times for each activity, the makespan Cmax, and machine_span
    starts = {}
    for act in activities:
        starts[act] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"start_{act}")

    Cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Cmax")
    machine_span = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="machine_span")

    model.update()

    # Precedence constraints: start_Y >= start_X + duration_X
    for (X, Y) in data["precedence"]:
        model.addConstr(starts[Y] >= starts[X] + dur[X], name=f"prec_{X}_{Y}")

    # Makespan constraints: Cmax >= start_i + duration_i for all i
    for act in activities:
        model.addConstr(Cmax >= starts[act] + dur[act], name=f"Cmax_after_{act}")

    # Machine rental span: machine_span = end_B - start_A
    model.addConstr(machine_span == (starts["B"] + dur["B"]) - starts["A"], name="machine_span_def")

    # Objective: minimize total cost
    work_cost = data["work_cost_per_project_day"]
    machine_cost = data["machine_rental_cost_per_day"]
    model.setObjective(work_cost * Cmax + machine_cost * machine_span, GRB.MINIMIZE)

    variables = {
        "start_A": starts["A"],
        "start_B": starts["B"],
        "start_C": starts["C"],
        "start_D": starts["D"],
        "start_E": starts["E"],
        "start_F": starts["F"],
        "start_G": starts["G"],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.SOLUTION_LIMIT: "SOLUTION_LIMIT",
        GRB.SUBOPTIMAL: "SUBOPTIMAL",
        GRB.CONTINUOUS: "CONTINUOUS",  # fallback, not an actual status
    }
    status_str = status_map.get(status_code, str(status_code))

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
        "machine_span": float(variables["machine_span"].X),
    }

    return {
        "status": status_str,
        "objective": objective,
        "solution": solution
    }