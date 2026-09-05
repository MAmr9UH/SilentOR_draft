import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict):
    model = gp.Model()
    # Optional: suppress output for cleaner runs
    model.setParam('OutputFlag', 0)

    M = 1e6  # big-M

    # Decision variables (as specified)
    y1_A = model.addVar(vtype=GRB.BINARY, name="y1_A")
    y1_B = model.addVar(vtype=GRB.BINARY, name="y1_B")
    y2_A = model.addVar(vtype=GRB.BINARY, name="y2_A")
    y2_B = model.addVar(vtype=GRB.BINARY, name="y2_B")
    y3_A = model.addVar(vtype=GRB.BINARY, name="y3_A")
    y3_B = model.addVar(vtype=GRB.BINARY, name="y3_B")

    skilled_t1_A = model.addVar(vtype=GRB.INTEGER, name="skilled_t1_A")
    skilled_t1_B = model.addVar(vtype=GRB.INTEGER, name="skilled_t1_B")
    skilled_t2_A = model.addVar(vtype=GRB.INTEGER, name="skilled_t2_A")
    skilled_t3_B = model.addVar(vtype=GRB.INTEGER, name="skilled_t3_B")

    labor_t1_B = model.addVar(vtype=GRB.INTEGER, name="labor_t1_B")
    labor_t2_B = model.addVar(vtype=GRB.INTEGER, name="labor_t2_B")
    labor_t3_A = model.addVar(vtype=GRB.INTEGER, name="labor_t3_A")
    labor_t3_B = model.addVar(vtype=GRB.INTEGER, name="labor_t3_B")

    total_skilled = model.addVar(vtype=GRB.INTEGER, name="total_skilled")
    total_labor = model.addVar(vtype=GRB.INTEGER, name="total_labor")

    variables = {
        "y1_A": y1_A,
        "y1_B": y1_B,
        "y2_A": y2_A,
        "y2_B": y2_B,
        "y3_A": y3_A,
        "y3_B": y3_B,
        "skilled_t1_A": skilled_t1_A,
        "skilled_t1_B": skilled_t1_B,
        "skilled_t2_A": skilled_t2_A,
        "skilled_t3_B": skilled_t3_B,
        "labor_t1_B": labor_t1_B,
        "labor_t2_B": labor_t2_B,
        "labor_t3_A": labor_t3_A,
        "labor_t3_B": labor_t3_B,
        "total_skilled": total_skilled,
        "total_labor": total_labor
    }

    # Data-derived constants
    hours1 = data["task_effective_hours"]["1"]
    hours2 = data["task_effective_hours"]["2"]
    hours3 = data["task_effective_hours"]["3"]

    # 1) Exactly one method per task
    model.addConstr(y1_A + y1_B == 1, name="task1_method")
    model.addConstr(y2_A + y2_B == 1, name="task2_method")
    model.addConstr(y3_A + y3_B == 1, name="task3_method")

    # Exclusion: if task 1 uses method B, task 3 cannot use pure-labor (A)
    model.addConstr(y1_B + y3_A <= 1, name="exclusion_t1B_t3A")

    # 2) Hours satisfaction (Big-M to allow inactive constraints when method not chosen)
    # Task 1
    model.addConstr(42 * skilled_t1_A >= hours1 - M * (1 - y1_A), name="t1_A_hours")
    model.addConstr(42 * skilled_t1_B + 36 * labor_t1_B >= hours1 - M * (1 - y1_B), name="t1_B_hours")

    # Task 2
    model.addConstr(42 * skilled_t2_A >= hours2 - M * (1 - y2_A), name="t2_A_hours")
    model.addConstr(36 * labor_t2_B >= hours2 - M * (1 - y2_B), name="t2_B_hours")

    # Task 3
    model.addConstr(36 * labor_t3_A >= hours3 - M * (1 - y3_A), name="t3_A_hours")
    model.addConstr(42 * skilled_t3_B + 36 * labor_t3_B >= hours3 - M * (1 - y3_B), name="t3_B_hours")

    # 3) Gating: if method not chosen, corresponding variables must be zero
    model.addConstr(skilled_t1_A <= M * y1_A, name="gate_t1_A")
    model.addConstr(skilled_t1_B <= M * y1_B, name="gate_t1_B")
    model.addConstr(labor_t1_B <= M * y1_B, name="gate_l1_B")

    model.addConstr(skilled_t2_A <= M * y2_A, name="gate_t2_A")
    model.addConstr(labor_t2_B <= M * y2_B, name="gate_l2_B")

    model.addConstr(labor_t3_A <= M * y3_A, name="gate_t3_A")
    model.addConstr(labor_t3_B <= M * y3_B, name="gate_l3_B")
    model.addConstr(skilled_t3_B <= M * y3_B, name="gate_t3_B")

    # Ratio constraints for group methods
    # Task 3 B: groups of 1 skilled and 3 laborers
    model.addConstr(labor_t3_B - 3 * skilled_t3_B == 0, name="ratio_t3_B")

    # Minimum skilled if task 3 uses B
    model.addConstr(skilled_t3_B >= 20 * y3_B, name="min_skilled_t3B")

    # 4) Totals and capacities
    model.addConstr(total_skilled == skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B, name="tot_skilled_eq")
    model.addConstr(total_labor == labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B, name="tot_labor_eq")

    max_skilled = data.get("max_skilled", None)
    max_labor = data.get("max_labor", None)
    if max_skilled is not None:
        model.addConstr(total_skilled <= max_skilled, name="cap_skilled")
    if max_labor is not None:
        model.addConstr(total_labor <= max_labor, name="cap_labor")

    # Total skilled cannot exceed 60% of total laborers
    model.addConstr(total_skilled <= 0.6 * total_labor, name="ratio_limit")

    # Objective: minimize weekly wages plus fixed setup cost for Task 1 B
    skilled_wage = data["weekly_wage"]["skilled"]
    labor_wage = data["weekly_wage"]["labor"]
    fixed_t1B = data["method_worker_requirements"]["task1_B"]["fixed_setup_cost"]

    objective = skilled_wage * total_skilled + labor_wage * total_labor + fixed_t1B * y1_B
    model.setObjective(objective, GRB.MINIMIZE)

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "Optimal"
    elif status_code == GRB.INFEASIBLE:
        status_str = "Infeasible"
    elif status_code == GRB.UNBOUNDED:
        status_str = "Unbounded"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TimeLimit"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "InfOrUnbd"
    else:
        status_str = str(status_code)

    obj_val = None
    if model.ObjVal is not None:
        obj_val = float(model.ObjVal)

    # Build solution dict
    sol_keys = [
        "y1_A","y1_B","y2_A","y2_B","y3_A","y3_B",
        "skilled_t1_A","skilled_t1_B","skilled_t2_A","skilled_t3_B",
        "labor_t1_B","labor_t2_B","labor_t3_A","labor_t3_B",
        "total_skilled","total_labor"
    ]
    solution = {}
    for k in sol_keys:
        v = variables[k]
        solution[k] = float(v.X)

    return {
        "status": status_str,
        "objective": obj_val if obj_val is not None else 0.0,
        "solution": solution
    }