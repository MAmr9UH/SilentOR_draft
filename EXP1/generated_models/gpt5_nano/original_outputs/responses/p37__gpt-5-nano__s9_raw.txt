import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Initialize model
    model = gp.Model()

    # Extract data
    months = data.get("months", [1, 2, 3])
    I0 = float(data["initial_inventory"])
    C0 = float(data["initial_cash"])
    capacity = float(data["capacity"])
    F = float(data["final_inventory_required"])

    p = {
        1: float(data["purchase_price"]["1"]),
        2: float(data["purchase_price"]["2"]),
        3: float(data["purchase_price"]["3"]),
    }
    sp = {
        1: float(data["selling_price"]["1"]),
        2: float(data["selling_price"]["2"]),
        3: float(data["selling_price"]["3"]),
    }

    # Decision variables
    buy_1 = model.addVar(lb=0.0, name="buy_1")
    buy_2 = model.addVar(lb=0.0, name="buy_2")
    buy_3 = model.addVar(lb=0.0, name="buy_3")

    sell_1 = model.addVar(lb=0.0, name="sell_1")
    sell_2 = model.addVar(lb=0.0, name="sell_2")
    sell_3 = model.addVar(lb=0.0, name="sell_3")

    inventory_1 = model.addVar(lb=0.0, ub=capacity, name="inventory_1")
    inventory_2 = model.addVar(lb=0.0, ub=capacity, name="inventory_2")
    inventory_3 = model.addVar(lb=0.0, ub=capacity, name="inventory_3")

    cash_1 = model.addVar(lb=0.0, name="cash_1")
    cash_2 = model.addVar(lb=0.0, name="cash_2")
    cash_3 = model.addVar(lb=0.0, name="cash_3")

    profit = model.addVar(lb=-GRB.INFINITY, name="profit")

    model.update()

    # Constraints

    # Inventory balance
    model.addConstr(inventory_1 == I0 + buy_1 - sell_1, name="inv_bal_1")
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="inv_bal_2")
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="inv_bal_3")

    # Capacity constraints (end-of-month inventories)
    model.addConstr(inventory_1 <= capacity, name="cap_1")
    model.addConstr(inventory_2 <= capacity, name="cap_2")
    model.addConstr(inventory_3 <= capacity, name="cap_3")

    # Sell from previous inventory only (same_month_purchases_sellable_next_month = True)
    model.addConstr(sell_1 <= I0, name="sell_from_inv_1")
    model.addConstr(sell_2 <= inventory_1, name="sell_from_inv_2")
    model.addConstr(sell_3 <= inventory_2, name="sell_from_inv_3")

    # Cash flow
    model.addConstr(cash_1 == C0 - buy_1 * p[1] + sell_1 * sp[1], name="cash_1_flow")
    model.addConstr(cash_2 == cash_1 - buy_2 * p[2] + sell_2 * sp[2], name="cash_2_flow")
    model.addConstr(cash_3 == cash_2 - buy_3 * p[3] + sell_3 * sp[3], name="cash_3_flow")

    # Cash nonnegativity
    model.addConstr(cash_1 >= 0, name="cash1_nonneg")
    model.addConstr(cash_2 >= 0, name="cash2_nonneg")
    model.addConstr(cash_3 >= 0, name="cash3_nonneg")

    # End inventory must be exactly final required
    model.addConstr(inventory_3 == F, name="final_inventory")

    # Profit definition
    model.addConstr(profit == (sell_1 * sp[1] + sell_2 * sp[2] + sell_3 * sp[3])
                           - (buy_1 * p[1] + buy_2 * p[2] + buy_3 * p[3]),
                    name="profit_def")

    # Objective: maximize profit
    model.setObjective(profit, GRB.MAXIMIZE)
    model.update()

    variables = {
        "buy_1": buy_1,
        "buy_2": buy_2,
        "buy_3": buy_3,
        "sell_1": sell_1,
        "sell_2": sell_2,
        "sell_3": sell_3,
        "inventory_1": inventory_1,
        "inventory_2": inventory_2,
        "inventory_3": inventory_3,
        "cash_1": cash_1,
        "cash_2": cash_2,
        "cash_3": cash_3,
        "profit": profit
    }

    return model, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    # Status handling
    status_code = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    status_str = status_map.get(status_code, str(status_code))

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    solution = {
        "buy_1": float(variables["buy_1"].X),
        "buy_2": float(variables["buy_2"].X),
        "buy_3": float(variables["buy_3"].X),
        "sell_1": float(variables["sell_1"].X),
        "sell_2": float(variables["sell_2"].X),
        "sell_3": float(variables["sell_3"].X),
        "inventory_1": float(variables["inventory_1"].X),
        "inventory_2": float(variables["inventory_2"].X),
        "inventory_3": float(variables["inventory_3"].X),
        "cash_1": float(variables["cash_1"].X),
        "cash_2": float(variables["cash_2"].X),
        "cash_3": float(variables["cash_3"].X),
        "profit": float(variables["profit"].X),
    }

    return {
        "status": status_str,
        "objective": objective_value,
        "solution": solution
    }