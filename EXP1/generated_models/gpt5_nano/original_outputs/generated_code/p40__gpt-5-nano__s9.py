import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    model = gp.Model("Task staffing optimization")

    # Decision variables
    y1_A = model.addVar(vtype=GRB.BINARY, name="y1_A")
    y1_B = model.addVar(vtype=GRB.BINARY, name="y1_B")

    y2_A = model.addVar(vtype=GRB.BINARY, name="y2_A")
    y2_B = model.addVar(vtype=GRB.BINARY, name="y2_B")

    y3_A = model.addVar(vtype=GRB.BINARY, name="y3_A")
    y3_B = model.addVar(vtype=GRB.BINARY, name="y3_B")

    skilled_t1_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="skilled_t1_A")
    skilled_t1_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="skilled_t1_B")

    skilled_t2_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="skilled_t2_A")
    skilled_t3_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="skilled_t3_B")

    labor_t1_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="labor_t1_B")
    labor_t2_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="labor_t2_B")
    labor_t3_A = model.addVar(vtype=GRB.INTEGER, lb=0, name="labor_t3_A")
    labor_t3_B = model.addVar(vtype=GRB.INTEGER, lb=0, name="labor_t3_B")

    total_skilled = model.addVar(vtype=GRB.INTEGER, lb=0, name="total_skilled")
    total_labor = model.addVar(vtype=GRB.INTEGER, lb=0, name="total_labor")

    model.update()

    # Group constraints: exactly one method per task
    model.addConstr(y1_A + y1_B == 1, name="one_method_t1")
    model.addConstr(y2_A + y2_B == 1, name="one_method_t2")
    model.addConstr(y3_A + y3_B == 1, name="one_method_t3")

    # Hours requirements (from data)
    demand = {
        "1": data["task_effective_hours"]["1"],
        "2": data["task_effective_hours"]["2"],
        "3": data["task_effective_hours"]["3"],
    }

    # Task 1: A
    model.addConstr(42 * skilled_t1_A >= demand["1"] * y1_A, name="t1_A_hours")
    # Task 1: B
    model.addConstr(42 * skilled_t1_B + 36 * labor_t1_B >= demand["1"] * y1_B, name="t1_B_hours")

    # Task 2: A
    model.addConstr(42 * skilled_t2_A >= demand["2"] * y2_A, name="t2_A_hours")
    # Task 2: B
    model.addConstr(36 * labor_t2_B >= demand["2"] * y2_B, name="t2_B_hours")

    # Task 3: A
    model.addConstr(36 * labor_t3_A >= demand["3"] * y3_A, name="t3_A_hours")
    # Task 3: B
    model.addConstr(42 * skilled_t3_B + 36 * labor_t3_B >= demand["3"] * y3_B, name="t3_B_hours")

    # Exclusion: if Task1 uses B, Task3 cannot use A
    model.addConstr(y1_B + y3_A <= 1, name="exclusion_t1B_t3A")

    # Minimum skilled if Task3 uses B
    model.addConstr(skilled_t3_B >= 20 * y3_B, name="min_skilled_if_task3_B")

    # Totals
    model.addConstr(total_skilled == skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B, name="total_skilled_sum")
    model.addConstr(total_labor == labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B, name="total_labor_sum")

    # Capacity constraints
    max_skilled = data["max_skilled"]
    max_labor = data["max_labor"]
    model.addConstr(total_skilled <= max_skilled, name="max_skilled")
    model.addConstr(total_labor <= max_labor, name="max_labor")

    # Ratio: total skilled cannot exceed 60% of total labor
    ratio = data["skilled_to_labor_ratio_max"]
    model.addConstr(total_skilled <= ratio * total_labor, name="ratio_limit")

    # Objective: minimize weekly wages plus fixed costs
    weekly_wage = data["weekly_wage"]
    skilled_wage = weekly_wage["skilled"]
    labor_wage = weekly_wage["labor"]

    fixed_cost_t1_B = data["method_worker_requirements"]["task1_B"].get("fixed_setup_cost", 0)

    objective = (
        skilled_wage * (skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B)
        + labor_wage * (labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B)
        + fixed_cost_t1_B * y1_B
    )

    model.setObjective(objective, GRB.MINIMIZE)

    # Expose variables map
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

    return model, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = "OTHER"

    # Ensure values are accessible
    model.update()

    solution = {
        "y1_A": float(variables["y1_A"].X),
        "y1_B": float(variables["y1_B"].X),
        "y2_A": float(variables["y2_A"].X),
        "y2_B": float(variables["y2_B"].X),
        "y3_A": float(variables["y3_A"].X),
        "y3_B": float(variables["y3_B"].X),
        "skilled_t1_A": float(variables["skilled_t1_A"].X),
        "skilled_t1_B": float(variables["skilled_t1_B"].X),
        "skilled_t2_A": float(variables["skilled_t2_A"].X),
        "skilled_t3_B": float(variables["skilled_t3_B"].X),
        "labor_t1_B": float(variables["labor_t1_B"].X),
        "labor_t2_B": float(variables["labor_t2_B"].X),
        "labor_t3_A": float(variables["labor_t3_A"].X),
        "labor_t3_B": float(variables["labor_t3_B"].X),
        "total_skilled": float(variables["total_skilled"].X),
        "total_labor": float(variables["total_labor"].X),
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }

    return result