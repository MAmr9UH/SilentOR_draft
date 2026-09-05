import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    # Decision variables
    y1_A = m.addVar(vtype=GRB.BINARY, name="y1_A")
    y1_B = m.addVar(vtype=GRB.BINARY, name="y1_B")

    y2_A = m.addVar(vtype=GRB.BINARY, name="y2_A")
    y2_B = m.addVar(vtype=GRB.BINARY, name="y2_B")

    y3_A = m.addVar(vtype=GRB.BINARY, name="y3_A")
    y3_B = m.addVar(vtype=GRB.BINARY, name="y3_B")

    skilled_t1_A = m.addVar(vtype=GRB.CONTINUOUS, name="skilled_t1_A")
    skilled_t1_B = m.addVar(vtype=GRB.CONTINUOUS, name="skilled_t1_B")

    skilled_t2_A = m.addVar(vtype=GRB.CONTINUOUS, name="skilled_t2_A")

    labor_t1_B = m.addVar(vtype=GRB.CONTINUOUS, name="labor_t1_B")
    labor_t2_B = m.addVar(vtype=GRB.CONTINUOUS, name="labor_t2_B")

    labor_t3_A = m.addVar(vtype=GRB.CONTINUOUS, name="labor_t3_A")
    skilled_t3_B = m.addVar(vtype=GRB.CONTINUOUS, name="skilled_t3_B")
    labor_t3_B = m.addVar(vtype=GRB.CONTINUOUS, name="labor_t3_B")

    total_skilled = m.addVar(vtype=GRB.CONTINUOUS, name="total_skilled")
    total_labor = m.addVar(vtype=GRB.CONTINUOUS, name="total_labor")

    m.update()

    # Exactly one method per task
    m.addConstr(y1_A + y1_B == 1, name="task1_choice")
    m.addConstr(y2_A + y2_B == 1, name="task2_choice")
    m.addConstr(y3_A + y3_B == 1, name="task3_choice")

    # Hours constraints based on methods
    h = data["task_effective_hours"]
    h1 = h["1"]; h2 = h["2"]; h3 = h["3"]

    m.addConstr(42 * skilled_t1_A == h1 * y1_A, name="t1_A_hours")
    m.addConstr(42 * skilled_t1_B == h1 * y1_B, name="t1_B_hours")

    m.addConstr(42 * skilled_t2_A ==