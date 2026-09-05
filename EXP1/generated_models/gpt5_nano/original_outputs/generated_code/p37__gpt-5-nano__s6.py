import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    m = gp.Model()

    # Data extraction
    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    p_buy = {1: data["purchase_price"]["1"],
             2: data["purchase_price"]["2"],
             3: data["purchase_price"]["3"]}

    p_sell = {1: data["selling_price"]["1"],
              2: data["selling_price"]["2"],
              3: data["selling_price"]["3"]}

    # Decision variables (flat, as requested)
    buy_1 = m.addVar(lb=0, name="buy_1")
    buy_2 = m.addVar(lb=0, name="buy_2")
    buy_3 = m.addVar(lb=0, name="buy_3")

    sell_1 = m.addVar(lb=0, name="sell_1")
    sell_2 = m.addVar(lb=0, name="sell_2")
    sell_3 = m.addVar(lb=0, name="sell_3")

    inventory_1 = m.addVar(lb=0, name="inventory_1")
    inventory_2 = m.addVar(lb=0, name="inventory_2")
    inventory_3 = m.addVar(lb=0, name="inventory_3")

    cash_1 = m.addVar(lb=0, name="cash_1")
    cash_2 = m.addVar(lb=0, name="cash_2")
    cash_3 = m.addVar(lb=0, name="cash_3")

    profit = m.addVar(lb=-GRB.INFINITY, name="profit")

    # Constraints
    # Inventory balance
    m.addConstr(inventory_1 == initial_inventory + buy_1 - sell_1, name="I1_balance")
    m.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="I2_balance")
    m.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="I3_balance")

    # Sell constraints (same-month purchases cannot be sold in the same month)
    m.addConstr(sell_1 <= initial_inventory, name="S1_cap")
    m.addConstr(sell_2 <= inventory_1, name="S2_cap")
    m.addConstr(sell_3 <= inventory_2, name="S3_cap")

    # Capacity constraints
    m.addConstr(inventory_1 <= capacity, name="I1_cap")
    m.addConstr(inventory_2 <= capacity, name="I2_cap")
    m.addConstr(inventory_3 <= capacity, name="I3_cap")

    # Final inventory requirement
    m.addConstr(inventory_3 == final_inventory_required, name="FinalInventory")

    # Cash flow
    m.addConstr(cash_1 == initial_cash - p_buy[1] * buy_1 + p_sell[1] * sell_1, name="Cash1")
    m.addConstr(cash_2 == cash_1 - p_buy[2] * buy_2 + p_sell[2] * sell_2, name="Cash2")
    m.addConstr(cash_3 == cash_2 - p_buy[3] * buy_3 + p_sell[3] * sell_3, name="Cash3")

    # Cash non-negativity
    m.addConstr(cash_1 >= 0, name="Cash1_nonneg")
    m.addConstr(cash_2 >= 0, name="Cash2_nonneg")
    m.addConstr(cash_3 >= 0, name="Cash3_nonneg")

    # Profit definition
    total_revenue = p_sell[1] * sell_1 + p_sell[2] * sell_2 + p_sell[3] * sell_3
    total_cost = p_buy[1] * buy_1 + p_buy[2] * buy_2 + p_buy[3] * buy_3
    m.addConstr(profit == total_revenue - total_cost, name="ProfitDef")

    # Objective
    m.setObjective(profit, GRB.MAXIMIZE)

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

    return m, variables


def solve(data: dict) -> dict:
    model, variables = build_model(data)
    model.optimize()

    status = model.Status
    if status == gp.GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status == gp.GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status == gp.GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status == gp.GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status == gp.GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status)

    # Read solution
    sol = {
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
        "profit": float(variables["profit"].X)
    }

    result = {
        "status": status_str,
        "objective": float(model.ObjVal) if status == gp.GRB.OPTIMAL or status == gp.GRB.TIME_LIMIT else None,
        "solution": sol
    }

    return result