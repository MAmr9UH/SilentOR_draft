import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model()
    durations = data["durations"]
    w_cost = data["work_cost_per_project_day"]
    m_cost = data["machine_rental_cost_per_day"]

    # Decision variables
    start_A = model.addVar(lb=0.0, name="start_A", vtype=GRB.CONTINUOUS)
    start_B = model.addVar(lb=0.0, name="start_B", vtype=GRB.CONTINUOUS)
    start_C = model.addVar(lb=0.0, name="start_C", vtype=GRB.CONTINUOUS)
    start_D = model.addVar(lb=0.0, name="start_D", vtype=GRB.CONTINUOUS)
    start_E = model.addVar(lb=0.0, name="start_E", vtype=GRB.CONTINUOUS)
    start_F = model.addVar(lb=0.0, name="start_F", vtype=GRB.CONTINUOUS)
    start_G = model.addVar(lb=0.0, name="start_G", vtype=GRB.CONTINUOUS)

    Cmax = model.addVar(lb=0.0, name="Cmax", vtype=GRB.CONTINUOUS)
    machine_span = model.addVar(lb=0.0, name="machine_span", vtype=GRB.CONTINUOUS)

    # Objective: minimize total cost
    model.setObjective(w_cost * Cmax + m_cost * machine_span, GRB.MINIMIZE)

    # Helper durations
    A = durations["A"]
    B = durations["B"]
    C = durations["C"]
    D = durations["D"]
    E = durations["E"]
    F = durations["F"]
    G = durations["G"]

    # Precedence constraints (expressed with start times and durations)
    model.addConstr(start_G >= start_A + A, name="A_to_G")
    model.addConstr(start_D >= start_A + A, name="A_to_D")

    model.addConstr(start_F >= start_E + E, name="E_to_F")
    model.addConstr(start_F >= start_G + G, name="G_to_F")

    model.addConstr(start_C >= start_D + D, name="D_to_C")
    model.addConstr(start_C >= start_F + F, name="F_to_C")

    model.addConstr(start_B >= start_F + F, name="F_to_B")

    # Cmax constraints to capture makespan
    model.addConstr(Cmax >= start_A + A, name="Cmax_A")
    model.addConstr(Cmax >= start_B + B, name="Cmax_B")
    model.addConstr(Cmax >= start_C + C, name="Cmax_C")
    model.addConstr(Cmax >= start_D + D, name="Cmax_D")
    model.addConstr(Cmax >= start_E + E, name="Cmax_E")
    model.addConstr(Cmax >= start_F + F, name="Cmax_F")
    model.addConstr(Cmax >= start_G + G, name="Cmax_G")

    # Machine rental span consistency: machine_span = end_B - start_A
    # end_B = start_B + B  => machine_span = (start_B + B) - start_A
    # => machine_span + start_A - start_B = B
    model.addConstr(machine_span + start_A - start_B == B, name="MachineSpan")

    variables = {
        "start_A": start_A,
        "start_B": start_B,
        "start_C": start_C,
        "start_D": start_D,
        "start_E": start_E,
        "start_F": start_F,
        "start_G": start_G,
        "Cmax": Cmax,
        "machine_span": machine_span
    }

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Map status to string
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT",
    }
    status_str = status_map.get(model.Status, str(model.Status))

    solution = {}
    for key in ["start_A","start_B","start_C","start_D","start_E","start_F","start_G","Cmax","machine_span"]:
        solution[key] = float(variables[key].X)

    result = {
        "status": status_str,
        "objective": float(model.ObjVal) if model.Status in (GRB.OPTIMAL, GRB.TIME_LIMIT, GRB.INFEASIBLE, GRB.UNBOUNDED) else None,
        "solution": solution
    }

    return result