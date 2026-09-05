import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("ProjectScheduling")

    durations = data["durations"]
    work_cost_per_day = data["work_cost_per_project_day"]
    machine_cost_per_day = data["machine_rental_cost_per_day"]

    # Decision variables: start times for A..G, Cmax, and machine_span
    start = {}
    for act in ["A", "B", "C", "D", "E", "F", "G"]:
        start[act] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"start_{act}")

    Cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Cmax")
    machine_span = model.addVar(vtype=GRB.CONTINUOUS, name="machine_span")

    model.update()

    # End time constraints: end_i <= Cmax
    for act in durations:
        model.addConstr(start[act] + durations[act] <= Cmax, name=f"end_before_Cmax_{act}")

    # Precedence constraints
    a_dur = durations["A"]
    model.addConstr(start["G"] >= start["A"] + a_dur, name="A_to_G")
    model.addConstr(start["D"] >= start["A"] + a_dur, name="A_to_D")

    model.addConstr(start["F"] >= start["E"] + durations["E"], name="E_to_F")
    model.addConstr(start["F"] >= start["G"] + durations["G"], name="G_to_F")

    model.addConstr(start["C"] >= start["D"] + durations["D"], name="D_to_C")
    model.addConstr(start["C"] >= start["F"] + durations["F"], name="F_to_C")

    model.addConstr(start["B"] >= start["F"] + durations["F"], name="F_to_B")

    # machine_span = end_B - start_A
    model.addConstr(machine_span == (start["B"] + durations["B"]) - start["A"], name="machine_span_eq")

    # Objective: minimize total cost
    objective = work_cost_per_day * Cmax + machine_cost_per_day * machine_span
    model.setObjective(objective, GRB.MINIMIZE)

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

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INTERRUPTED: "INTERRUPTED"
    }
    status_str = status_map.get(model.Status, str(model.Status))
    obj_val = model.ObjVal

    solution = {}
    for key in ["start_A","start_B","start_C","start_D","start_E","start_F","start_G","Cmax","machine_span"]:
        solution[key] = variables[key].X

    return {
        "status": status_str,
        "objective": float(obj_val),
        "solution": solution
    }