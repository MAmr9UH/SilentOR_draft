import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    model = gp.Model()
    model.setParam("OutputFlag", 0)

    # Decision variables
    h = {}
    y = {}
    for student in data["students"]:
        for day in data["days"]:
            h[student, day] = model.addVar(
                vtype=GRB.CONTINUOUS,
                lb=0,
                ub=data["availability_hours"][str(student)][day],
                name=f"h_{student}_{day}"
            )
            y[student, day] = model.addVar(
                vtype=GRB.BINARY, name=f"y_{student}_{day}"
            )

    # Objective function
    model.setObjective(
        gp.quicksum(
            data["wage"][str(student)] * h[student, day]
            for student in data["students"]
            for day in data["days"]
        ),
        GRB.MINIMIZE
    )

    # Constraints
    # Each student must work at least minimum weekly hours
    for student in data["undergraduates"]:
        model.addConstr(
            gp.quicksum(h[student, day] for day in data["days"]) >=
            data["minimum_weekly_hours_undergrad"],
            name=f"weekly_hours_{student}"
        )
    for student in data["graduates"]:
        model.addConstr(
            gp.quicksum(h[student, day] for day in data["days"]) >=
            data["minimum_weekly_hours_grad"],
            name=f"weekly_hours_{student}"
        )

    # Each student can work no more than 2 shifts per week
    for student in data["students"]:
        model.addConstr(
            gp.quicksum(y[student, day] for day in data["days"]) <=
            data["max_shifts_per_week"],
            name=f"max_shifts_{student}"
        )

    # No more than 3 students can be scheduled for duty each day
    for day in data["days"]:
        model.addConstr(
            gp.quicksum(y[student, day] for student in data["students"]) <=
            data["max_students_per_day"],
            name=f"max_students_per_day_{day}"
        )

    # Hours worked must be less than or equal to the binary variable times the maximum hours available
    for student in data["students"]:
        for day in data["days"]:
            model.addConstr(
                h[student, day] <= data["availability_hours"][str(student)][day] * y[student, day],
                name=f"hour_limit_{student}_{day}"
            )

    # Each day must have exactly one student on duty for the full open hours
    for day in data["days"]:
        model.addConstr(
            gp.quicksum(h[student, day] for student in data["students"]) == \
            data["open_hours_per_day"],
            name=f"duty_hours_{day}"
        )

    variables = {
        "variables_keys": {
            "h_1_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_1_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_1_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_1_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_1_Fri": "continuous Var: duty hours assigned to this student on this day",
            "h_2_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_2_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_2_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_2_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_2_Fri": "continuous Var: duty hours assigned to this student on this day",
            "h_3_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_3_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_3_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_3_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_3_Fri": "continuous Var: duty hours assigned to this student on this day",
            "h_4_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_4_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_4_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_4_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_4_Fri": "continuous Var: duty hours assigned to this student on this day",
            "h_5_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_5_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_5_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_5_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_5_Fri": "continuous Var: duty hours assigned to this student on this day",
            "h_6_Mon": "continuous Var: duty hours assigned to this student on this day",
            "h_6_Tue": "continuous Var: duty hours assigned to this student on this day",
            "h_6_Wed": "continuous Var: duty hours assigned to this student on this day",
            "h_6_Thu": "continuous Var: duty hours assigned to this student on this day",
            "h_6_Fri": "continuous Var: duty hours assigned to this student on this day",
            "y_1_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_1_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_1_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_1_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_1_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_2_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_2_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_2_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_2_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_2_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_3_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_3_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_3_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_3_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_3_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_4_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_4_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_4_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_4_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_4_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_5_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_5_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_5_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_5_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_5_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_6_Mon": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_6_Tue": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_6_Wed": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_6_Thu": "binary Var: 1 if this student is scheduled for a shift on this day",
            "y_6_Fri": "binary Var: 1 if this student is scheduled for a shift on this day",
        }
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    if model.Status != GRB.OPTIMAL:
        return {
            "status": "infeasible_or_unbounded",
            "objective": None,
            "solution": {}
        }

    solution = {
        "h_1_Mon": float(h[1, "Mon"].X),
        "h_1_Tue": float(h[1, "Tue"].X),
        "h_1_Wed": float(h[1, "Wed"].X),
        "h_1_Thu": float(h[1, "Thu"].X),
        "h_1_Fri": float(h[1, "Fri"].X),
        "h_2_Mon": float(h[2, "Mon"].X),
        "h_2_Tue": float(h[2, "Tue"].X),
        "h_2_Wed": float(h[2, "Wed"].X),
        "h_2_Thu": float(h[2, "Thu"].X),
        "h_2_Fri": float(h[2, "Fri"].X),
        "h_3_Mon": float(h[3, "Mon"].X),
        "h_3_Tue": float(h[3, "Tue"].X),
        "h_3_Wed": float(h[3, "Wed"].X),
        "h_3_Thu": float(h[3, "Thu"].X),
        "h_3_Fri": float(h[3, "Fri"].X),
        "h_4_Mon": float(h[4, "Mon"].X),
        "h_4_Tue": float(h[4, "Tue"].X),
        "h_4_Wed": float(h[4, "Wed"].X),
        "h_4_Thu": float(h[4, "Thu"].X),
        "h_4_Fri": float(h[4, "Fri"].X),
        "h_5_Mon": float(h[5, "Mon"].X),
        "h_5_Tue": float(h[5, "Tue"].X),
        "h_5_Wed": float(h[5, "Wed"].X),
        "h_5_Thu": float(h[5, "Thu"].X),
        "h_5_Fri": float(h[5, "Fri"].X),
        "h_6_Mon": float(h[6, "Mon"].X),
        "h_6_Tue": float(h[6, "Tue"].X),
        "h_6_Wed": float(h[6, "Wed"].X),
        "h_6_Thu": float(h[6, "Thu"].X),
        "h_6_Fri": float(h[6, "Fri"].X),
        "y_1_Mon": float(y[1, "Mon"].X),
        "y_1_Tue": float(y[1, "Tue"].X),
        "y_1_Wed": float(y[1, "Wed"].X),
        "y_1_Thu": float(y[1, "Thu"].X),
        "y_1_Fri": float(y[1, "Fri"].X),
        "y_2_Mon": float(y[2, "Mon"].X),
        "y_2_Tue": float(y[2, "Tue"].X),
        "y_2_Wed": float(y[2, "Wed"].X),
        "y_2_Thu": float(y[2, "Thu"].X),
        "y_2_Fri": float(y[2, "Fri"].X),
        "y_3_Mon": float(y[3, "Mon"].X),
        "y_3_Tue": float(y[3, "Tue"].X),
        "y_3_Wed": float(y[3, "Wed"].X),
        "y_3_Thu": float(y[3, "Thu"].X),
        "y_3_Fri": float(y[3, "Fri"].X),
        "y_4_Mon": float(y[4, "Mon"].X),
        "y_4_Tue": float(y[4, "Tue"].X),
        "y_4_Wed": float(y[4, "Wed"].X),
        "y_4_Thu": float(y[4, "Thu"].X),
        "y_4_Fri": float(y[4, "Fri"].X),
        "y_5_Mon": float(y[5, "Mon"].X),
        "y_5_Tue": float(y[5, "Tue"].X),
        "y_5_Wed": float(y[5, "Wed"].X),
        "y_5_Thu": float(y[5, "Thu"].X),
        "y_5_Fri": float(y[5, "Fri"].X),
        "y_6_Mon": float(y[6, "Mon"].X),
        "y_6_Tue": float(y[6, "Tue"].X),
        "y_6_Wed": float(y[6, "Wed"].X),
        "y_6_Thu": float(y[6, "Thu"].X),
        "y_6_Fri": float(y[6, "Fri"].X),
    }

    return {
        "status": "optimal",
        "objective": float(model.ObjVal),
        "solution": solution
    }