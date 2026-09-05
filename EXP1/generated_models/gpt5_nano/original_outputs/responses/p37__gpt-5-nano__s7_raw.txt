import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    months = data.get("months", [1, 2, 3])
    I0 = data["initial_inventory"]
    C0 = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    purchase_price = data["purchase_price"]  # dict with keys "1","2","3"
    selling_price = data["selling_price"]    # dict with keys "1","2","3"

    model = gp.Model()

    # Decision variables
    buy_1 = model.addVar(lb=0.0, name="buy_1", vtype=GRB.CONTINUOUS)
    buy_2 = model.addVar(lb=0.0, name="buy_2", vtype=GRB.CONTINUOUS)
    buy_3 = model.addVar(lb=0.0, name="buy_3", vtype=GRB.CONTINUOUS)

    sell_1 = model.addVar(lb=0.0, name="sell_1", vtype=GRB.CONTINUOUS)
    sell_2 = model.addVar(lb=0.0, name="sell_2", vtype=GRB.CONTINUOUS)
    sell_3 = model.addVar(lb=0.0, name="sell_3", vtype=GRB.CONTINUOUS)

    inventory_1 = model.addVar(lb=0.0, name="inventory_1", vtype=GRB.CONTINUOUS)
    inventory_2 = model.addVar(lb=0.0, name="inventory_2", vtype=GRB.CONTINUOUS)
    inventory_3 = model.addVar(lb=0.0, name="inventory_3", vtype=GRB.CONTINUOUS)

    cash_1 = model.addVar(lb=0.0, name="cash_1", vtype=GRB.CONTINUOUS)
    cash_2 = model.addVar(lb=0.0, name="cash_2", vtype=GRB.CONTINUOUS)
    cash_3 = model.addVar(lb=0.0, name="cash_3", vtype=GRB.CONTINUOUS)

    profit = model.addVar(lb=-GRB.INFINITY, name="profit", vtype=GRB.CONTINUOUS)

    model.update()

    p1 = purchase_price[str(1)]
    p2 = purchase_price[str(2)]
    p3 = purchase_price[str(3)]
    s1 = selling_price[str(1)]
    s2 = selling_price[str(2)]
    s3 = selling_price[str(3)]

    # Constraints

    # Cash flow
    model.addConstr(cash_1 == C0 - buy_1 * p1 + sell_1 * s1, name="cash_flow_1")
    model.addConstr(cash_2 == cash_1 - buy_2 * p2 + sell_2 * s2, name="cash_flow_2")
    model.addConstr(cash_3 == cash_2 - buy_3 * p3 + sell_3 * s3, name="cash_flow_3")

    # Inventory balance
    model.addConstr(inventory_1 == I0 - sell_1 + buy_1, name="inventory_balance_1")
    model.addConstr(inventory_2 == inventory_1 - sell_2 + buy_2, name="inventory_balance_2")
    model.addConstr(inventory_3 == inventory_2 - sell_3 + buy_3, name="inventory_balance_3")

    # Final inventory requirement
    model.addConstr(inventory_3 == final_inventory_required, name="final_inventory")

    # Capacity constraints
    model.addConstr(inventory_1 <= capacity, name="cap1")
    model.addConstr(inventory_2 <= capacity, name="cap2")
    model.addConstr(inventory_3 <= capacity, name="cap3")

    # Non-negativity of revenues and flow (already via LB=0 for buys/sells, inventories, cash)
    model.addConstr(inventory_1 >= 0, name="inv1_nonneg")
    model.addConstr(inventory_2 >= 0, name="inv2_nonneg")
    model.addConstr(inventory_3 >= 0, name="inv3_nonneg")
    model.addConstr(cash_1 >= 0, name="cash1_nonneg")
    model.addConstr(cash_2 >= 0, name="cash2_nonneg")
    model.addConstr(cash_3 >= 0, name="cash3_nonneg")

    # Lag constraints: you can only sell inventory from previous month
    model.addConstr(sell_1 <= I0, name="sell1_limit")
    model.addConstr(sell_2 <= inventory_1, name="sell2_limit")
    model.addConstr(sell_3 <= inventory_2, name="sell3_limit")

    # Profit definition
    model.addConstr(profit == (sell_1 * s1 - buy_1 * p1) +
                               (sell_2 * s2 - buy_2 * p2) +
                               (sell_3 * s3 - buy_3 * p3),
                    name="profit_def")

    # Objective
    model.setObjective(profit, GRB.MAXIMIZE)

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

    status_int = model.Status
    if status_int == GRB.OPTIMAL:
        status_str = "OPTIMAL"
    elif status_int == GRB.INFEASIBLE:
        status_str = "INFEASIBLE"
    elif status_int == GRB.UNBOUNDED:
        status_str = "UNBOUNDED"
    elif status_int == GRB.INF_OR_UNBD:
        status_str = "INF_OR_UNBD"
    elif status_int == GRB.TIME_LIMIT:
        status_str = "TIME_LIMIT"
    else:
        status_str = str(status_int)

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
        "profit": float(variables["profit"].X)
    }

    return {
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }