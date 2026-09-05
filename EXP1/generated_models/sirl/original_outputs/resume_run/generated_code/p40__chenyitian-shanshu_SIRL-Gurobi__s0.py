import gurobipy as gp
from gurobipy import GRB
import math

def build_model(data: dict) -> tuple:
    model = gp.Model("task_allocation_model")

    # Decision variables
    y1_A = model.addVar(name="y1_A", vtype=GRB.BINARY)
    y1_B = model.addVar(name="y1_B", vtype=GRB.BINARY)
    y2_A = model.addVar(name="y2_A", vtype=GRB.BINARY)
    y2_B = model.addVar(name="y2_B", vtype=GRB.BINARY)
    y3_A = model.addVar(name="y3_A", vtype=GRB.BINARY)
    y3_B = model.addVar(name="y3_B", vtype=GRB.BINARY)
    
    skilled_t1_A = model.addVar(name="skilled_t1_A", vtype=GRB.INTEGER, lb=0)
    skilled_t1_B = model.addVar(name="skilled_t1_B", vtype=GRB.INTEGER, lb=0)
    skilled_t2_A = model.addVar(name="skilled_t2_A", vtype=GRB.INTEGER, lb=0)
    skilled_t3_B = model.addVar(name="skilled_t3_B", vtype=GRB.INTEGER, lb=0)
    labor_t1_B = model.addVar(name="labor_t1_B", vtype=GRB.INTEGER, lb=0)
    labor_t2_B = model.addVar(name="labor_t2_B", vtype=GRB.INTEGER, lb=0)
    labor_t3_A = model.addVar(name="labor_t3_A", vtype=GRB.INTEGER, lb=0)
    labor_t3_B = model.addVar(name="labor_t3_B", vtype=GRB.INTEGER, lb=0)
    
    total_skilled = model.addVar(name="total_skilled", vtype=GRB.INTEGER, lb=0)
    total_labor = model.addVar(name="total_labor", vtype=GRB.INTEGER, lb=0)

    # Objective function: Minimize total weekly cost
    weekly_wage = data["weekly_wage"]
    weekly_effective_hours = data["weekly_effective_hours"]
    task_effective_hours = data["task_effective_hours"]
    method_worker_requirements = data["method_worker_requirements"]
    
    model.setObjective(
        (weekly_wage["skilled"] * (skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B) +
         weekly_wage["labor"] * (labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B) +
         500 * y1_B +
         method_worker_requirements["task1_B"]["fixed_setup_cost"] * y1_B +
         method_worker_requirements["task2_B"]["fixed_setup_cost"] * y2_B +
         method_worker_requirements["task3_B"]["fixed_setup_cost"] * y3_B),
        GRB.MINIMIZE)

    # Task 1 effective hours
    model.addConstr(8400 * (method_worker_requirements["task1_A"]["skilled"] * y1_A + method_worker_requirements["task1_B"]["skilled"] * y1_B) +
                    36 * 2 * method_worker_requirements["task1_B"]["labor"] * y1_B == 8400)

    # Task 2 effective hours
    model.addConstr(10800 * (method_worker_requirements["task2_A"]["skilled"] * y2_A + method_worker_requirements["task2_B"]["skilled"] * y2_B) +
                    36 * 3 * method_worker_requirements["task2_B"]["labor"] * y2_B == 10800)

    # Task 3 effective hours
    model.addConstr(18000 * (method_worker_requirements["task3_A"]["skilled"] * y3_A + method_worker_requirements["task3_B"]["skilled"] * y3_B) +
                    36 * 5 * method_worker_requirements["task3_A"]["labor"] * y3_A +
                    36 * 3 * method_worker_requirements["task3_B"]["labor"] * y3_B == 18000)

    # Maximum number of skilled workers
    model.addConstr(skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B <= 400)

    # Maximum number of laborers
    model.addConstr(labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B <= 800)

    # Total number of skilled workers
    model.addConstr(total_skilled == skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B)

    # Total number of laborers
    model.addConstr(total_labor == labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B)

    # Skilled workers to laborers ratio
    model.addConstr(total_skilled <= 0.6 * total_labor)

    # If task 1 uses method B, task 3 cannot use method A
    model.addConstr(y1_B + y3_A <= 1)

    # If task 3 uses method B, at least 20 skilled workers must be assigned
    model.addConstr(y3_B * 20 <= skilled_t3_B)

    # Objective function: Minimize total weekly cost
    weekly_wage_skilled = weekly_wage["skilled"]
    weekly_wage_labor = weekly_wage["labor"]
    weekly_hours_skilled = weekly_effective_hours["skilled"]
    weekly_hours_labor = weekly_effective_hours["labor"]

    # Calculate total wage for each task
    model.addConstr(
        weekly_wage_skilled * (skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B) +
        weekly_wage_labor * (labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B) +
        500 * y1_B +
        method_worker_requirements["task1_B"]["fixed_setup_cost"] * y1_B +
        method_worker_requirements["task2_B"]["fixed_setup_cost"] * y2_B +
        method_worker_requirements["task3_B"]["fixed_setup_cost"] * y3_B
    )

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

    if model.status == GRB.OPTIMAL:
        solution = {
            "y1_A": variables["y1_A"].x,
            "y1_B": variables["y1_B"].x,
            "y2_A": variables["y2_A"].x,
            "y2_B": variables["y2_B"].x,
            "y3_A": variables["y3_A"].x,
            "y3_B": variables["y3_B"].x,
            "skilled_t1_A": variables["skilled_t1_A"].x,
            "skilled_t1_B": variables["skilled_t1_B"].x,
            "skilled_t2_A": variables["skilled_t2_A"].x,
            "skilled_t3_B": variables["skilled_t3_B"].x,
            "labor_t1_B": variables["labor_t1_B"].x,
            "labor_t2_B": variables["labor_t2_B"].x,
            "labor_t3_A": variables["labor_t3_A"].x,
            "labor_t3_B": variables["labor_t3_B"].x,
            "total_skilled": variables["total_skilled"].x,
            "total_labor": variables["total_labor"].x
        }
        return {
            "status": "OPTIMAL",
            "objective": model.objVal,
            "solution": solution
        }
    else:
        return {
            "status": "INFEASIBLE",
            "objective": None,
            "solution": None
        }