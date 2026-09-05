import sys
from gurobipy import Model, GRB

def build_model(data: dict):
    m = Model()

    # Binary method-choice variables
    y1_A = m.addVar(vtype=GRB.BINARY, name="y1_A")
    y1_B = m.addVar(vtype=GRB.BINARY, name="y1_B")
    y2_A = m.addVar(vtype=GRB.BINARY, name="y2_A")
    y2_B = m.addVar(vtype=GRB.BINARY, name="y2_B")
    y3_A = m.addVar(vtype=GRB.BINARY, name="y3_A")
    y3_B = m.addVar(vtype=GRB.BINARY, name="y3_B")

    # Task-specific worker allocations (continuous allowed)
    skilled_t1_A = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="skilled_t1_A")
    skilled_t1_B = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="skilled_t1_B")
    skilled_t2_A = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="skilled_t2_A")
    skilled_t3_B = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="skilled_t3_B")

    labor_t1_B = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="labor_t1_B")
    labor_t2_B = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="labor_t2_B")
    labor_t3_A = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="labor_t3_A")
    labor_t3_B = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="labor_t3_B")

    # Totals
    total_skilled = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="total_skilled")
    total_labor = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name="total_labor")

    m.update()

    # Constraints: exactly one method per task
    m.addConstr(y1_A + y1_B == 1, name="task1_method")
    m.addConstr(y2_A + y2_B == 1, name="task2_method")
    m.addConstr(y3_A + y3_B == 1, name="task3_method")

    # Method-resource realizations (fixed per method)
    # Task 1
    m.addConstr(skilled_t1_A == 200.0 * y1_A)
    m.addConstr(skilled_t1_B == 200.0 * y1_B)
    m.addConstr(labor_t1_B == 400.0 * y1_B)

    # Task 2
    m.addConstr(skilled_t2_A == 257.14285714285717 * y2_A)
    m.addConstr(labor_t2_B == 300.0 * y2_B)

    # Task 3
    m.addConstr(labor_t3_A == 500.0 * y3_A)
    m.addConstr(skilled_t3_B == 120.0 * y3_B)
    m.addConstr(labor_t3_B == 360.0 * y3_B)

    # Totals equal sum of allocated workers
    m.addConstr(total_skilled - (skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B) == 0)
    m.addConstr(total_labor - (labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B) == 0)

    # Global constraints
    max_skilled = data.get("max_skilled", 0)
    max_labor = data.get("max_labor", 0)
    m.addConstr(total_skilled <= max_skilled)
    m.addConstr(total_labor <= max_labor)

    ratio_max = data.get("skilled_to_labor_ratio_max", 0.0)
    m.addConstr(total_skilled <= ratio_max * total_labor)

    # Exclusion: if task 1 uses B, task 3 cannot use A
    m.addConstr(y1_B + y3_A <= 1)

    # If Task 3 uses mixed method, at least 20 skilled workers must be assigned
    minimum_skilled_if_task3_B = data.get("minimum_skilled_if_task3_B", 0)
    m.addConstr(total_skilled >= minimum_skilled_if_task3_B * y3_B)

    # Objective: minimize weekly wages plus fixed costs
    weekly_wage_skilled = data.get("weekly_wage", {}).get("skilled", 0.0)
    weekly_wage_labor = data.get("weekly_wage", {}).get("labor", 0.0)
    fixed_cost_task1_B = 0.0
    try:
        fixed_cost_task1_B = data["method_worker_requirements"]["task1_B"].get("fixed_setup_cost", 0.0)
    except Exception:
        fixed_cost_task1_B = 0.0

    objective = weekly_wage_skilled * total_skilled + weekly_wage_labor * total_labor + fixed_cost_task1_B * y1_B
    m.setObjective(objective, GRB.MINIMIZE)

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

    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Prepare status string
    st = model.Status
    if st == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif st == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif st == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif st == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif st == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(st)

    obj_val = float(model.ObjVal)

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
        "total_labor": float(variables["total_labor"].X)
    }

    return {
        "status": status_str,
        "objective": obj_val,
        "solution": solution
    }