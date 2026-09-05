import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    durations = data["durations"]
    activities = data["activities"]
    precedence = data["precedence"]
    work_cost_per_day = data["work_cost_per_project_day"]
    machine_rental_per_day = data["machine_rental_cost_per_day"]

    model = gp.Model("ProjectScheduling")

    # Decision variables
    start_vars = {}
    for a in activities:
        start_vars[a] = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"start_{a}")

    Cmax = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="Cmax")
    machine_span = model.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="machine_span")

    # Objective: minimize total project cost
    model.setObjective(work_cost_per_day * Cmax + machine_rental_per_day * machine_span, GRB.MINIMIZE)

    # Precedence constraints: s_succ >= s_pre + dur_pre
    for pre, succ in precedence:
        model.addConstr(start_vars[succ] >= start_vars[pre] + durations[pre])

    # Makespan constraints: end_i <= Cmax  -> s_i + dur_i <= Cmax
    for a in activities:
        model.addConstr(start_vars[a] + durations[a] <= Cmax)

    # Machine span equality: machine_span = end_B - start_A
    model.addConstr(machine_span == start_vars["B"] + durations["B"] - start_vars["A"])

    variables = {
        "start_A": start_vars["A"],
        "start_B": start_vars["B"],
        "start_C": start_vars["C"],
        "start_D": start_vars["D"],
        "start_E": start_vars["E"],
        "start_F": start_vars["F"],
        "start_G": start_vars["G"],
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    model.update()
    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    st = model.Status
    status_str = status_map.get(st, str(st))

    # Read solution values
    solution = {}
    for key in ["start_A","start_B","start_C","start_D","start_E","start_F","start_G","Cmax","machine_span"]:
        solution[key] = float(variables[key].X)

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": {
            "start_A": solution["start_A"],
            "start_B": solution["start_B"],
            "start_C": solution["start_C"],
            "start_D": solution["start_D"],
            "start_E": solution["start_E"],
            "start_F": solution["start_F"],
            "start_G": solution["start_G"],
            "Cmax": solution["Cmax"],
            "machine_span": solution["machine_span"]
        }
    }
    return result