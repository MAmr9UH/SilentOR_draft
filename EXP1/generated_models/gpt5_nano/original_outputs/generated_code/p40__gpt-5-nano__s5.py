import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    """
    Build and return a Gurobi model and a dictionary of variable objects.
    The function does not call optimize().
    """
    model = gp.Model()

    # Decision variables
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

    # Objective: minimize weekly wages + fixed setup cost for Task 1B
    skilled_wage = data["weekly_wage"]["skilled"]
    labor_wage = data["weekly_wage"]["labor"]
    setup_cost = data["method_worker_requirements"]["task1_B"]["fixed_setup_cost"]

    model.setObjective(skilled_wage * total_skilled + labor_wage * total_labor + setup_cost * y1_B, GRB.MINIMIZE)

    # Constraints
    M = 100000  # large constant for Big-M

    # One method per task
    model.addConstr(y1_A + y1_B == 1, name="task1_method")
    model.addConstr(y2_A + y2_B == 1, name="task2_method")
    model.addConstr(y3_A + y3_B == 1, name="task3_method")

    # Exclusion: If Task 1 uses B, Task 3 cannot use A
    model.addConstr(y1_B + y3_A <= 1, name="exclusion_1_3")

    # Totals
    model.addConstr(total_skilled == skilled_t1_A + skilled_t1_B + skilled_t2_A + skilled_t3_B,
                    name="total_skilled_def")
    model.addConstr(total_labor == labor_t1_B + labor_t2_B + labor_t3_A + labor_t3_B,
                    name="total_labor_def")

    # Capacity constraints
    model.addConstr(total_skilled <= data["max_skilled"], name="skilled_cap")
    model.addConstr(total_labor <= data["max_labor"], name="labor_cap")
    model.addConstr(total_skilled <= data["