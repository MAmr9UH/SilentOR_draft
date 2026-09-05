"""Certified base model for Exp-2 problem 30 (three_year_investment_cash_flow_lp).
Maximize principal+interest at end of year 3. Cash-flow balance each year; project limits.
Returns keys x_annual_y1..3, x_project2_y1, x_project3_y2, x_project4_y3, cash_after_y1..3,
final_amount."""
import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    F = data["initial_fund"]
    rA = data["annual_project_return"]      # 1.2 (one-year 20%)
    r2 = data["project2_return"]; lim2 = data["project2_limit"]   # 1.5, <=150000, Y1->end Y2
    r3 = data["project3_return"]; lim3 = data["project3_limit"]   # 1.6, <=200000, Y2->end Y3
    r4 = data["project4_return"]; lim4 = data["project4_limit"]   # 1.4, <=100000, Y3->end Y3
    m = gp.Model(); m.Params.OutputFlag = 0

    xA1 = m.addVar(lb=0, name="x_annual_y1")
    xA2 = m.addVar(lb=0, name="x_annual_y2")
    xA3 = m.addVar(lb=0, name="x_annual_y3")
    xP2 = m.addVar(lb=0, name="x_project2_y1")
    xP3 = m.addVar(lb=0, name="x_project3_y2")
    xP4 = m.addVar(lb=0, name="x_project4_y3")
    c1 = m.addVar(lb=0, name="cash_after_y1")
    c2 = m.addVar(lb=0, name="cash_after_y2")
    c3 = m.addVar(lb=0, name="cash_after_y3")
    fin = m.addVar(lb=0, name="final_amount")

    # R_year1_budget: beginning Y1 investments + carried cash == initial fund
    m.addConstr(xA1 + xP2 + c1 == F, name="year1_budget")
    # R_year2_budget: beginning Y2 investments + carried cash == cash carried + annual Y1 return
    m.addConstr(xA2 + xP3 + c2 <= c1 + rA * xA1, name="year2_budget")
    # R_year3_budget: beginning Y3 investments + carried cash == cash carried + Y2 annual return
    #                 + project2 maturing (invested Y1, recovered end Y2)
    m.addConstr(xA3 + xP4 + c3 == c2 + rA * xA2 + r2 * xP2, name="year3_budget")
    # R_final_balance: final == carried cash + Y3 annual return + project3 + project4 maturing
    m.addConstr(fin == c3 + rA * xA3 + r3 * xP3 + r4 * xP4, name="final_balance")

    # R_limit_project2/3/4
    m.addConstr(xP2 <= lim2, name="limit_project2")
    m.addConstr(xP3 <= lim3, name="limit_project3")
    m.addConstr(xP4 <= lim4, name="limit_project4")

    # R_obj: maximize final amount
    m.setObjective(fin, GRB.MAXIMIZE)

    variables = {"x_annual_y1": xA1, "x_annual_y2": xA2, "x_annual_y3": xA3,
                 "x_project2_y1": xP2, "x_project3_y2": xP3, "x_project4_y3": xP4,
                 "cash_after_y1": c1, "cash_after_y2": c2, "cash_after_y3": c3,
                 "final_amount": fin}
    return m, variables


def solve(data: dict) -> dict:
    m, variables = build_model(data)
    m.optimize()
    status_map = {GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE",
                  GRB.UNBOUNDED: "UNBOUNDED", GRB.INF_OR_UNBD: "INF_OR_UNBD",
                  GRB.TIME_LIMIT: "TIME_LIMIT"}
    sol = {k: float(v.X) for k, v in variables.items()}
    return {"status": status_map.get(m.Status, str(m.Status)),
            "objective": float(m.ObjVal), "solution": sol}
