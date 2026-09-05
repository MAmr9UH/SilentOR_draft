import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    m = gp.Model()

    # Parameters from data
    initial_inventory = data["initial_inventory"]
    initial_cash = data["initial_cash"]
    capacity = data["capacity"]
    final_inventory_required = data["final_inventory_required"]

    purchase_price = data["purchase_price"]
    selling_price = data["selling_price"]

    p1 = float(purchase_price["1"])
    p2 = float(purchase_price["2"])
    p3 = float(purchase_price["3"])

    sp1 = float(selling_price["1"])
    sp2 = float(selling_price["2"])
    sp3 = float(selling_price["3"])

    # Decision variables (flat)
    buy_1 = m.addVar(lb=0.0, name="buy_1")
    buy_2 = m.addVar(lb=0.0, name="buy_2")
    buy_3 = m.addVar(lb=0.0, name="buy_3")

    sell_1 = m.addVar(lb=0.0, name="sell_1")
    sell_2 = m.addVar(lb=0.0, name="sell_2")
    sell_3 = m.addVar(lb=0.0, name="sell_3")

    inventory_1 = m.addVar(lb=0.0, ub=capacity, name="inventory_1")
    inventory_2 = m.addVar(lb=0.0, ub=capacity, name="inventory_2")
    inventory_3 = m.addVar(lb=0.0, ub=capacity, name="inventory_3")

    cash_1 = m.addVar(lb=0.0, name="cash_1")
    cash_2 = m.addVar(lb=0.0, name="cash_2")
    cash_3 = m.addVar(lb=0.0, name="cash_3")

    profit = m.addVar(lb=-GRB.INFINITY, name="profit")

    # Constraints

    # Inventory balances
    m.addConstr(inventory_1 == initial_inventory + buy_1 - sell_1, name="inv1_balance")
    m.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="inv2_balance")
    m.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="inv3_balance")

    # Final inventory requirement
    m.addConstr(inventory_3 == final_inventory_required, name="final_inventory")

    # Sell constraints (same-month purchases cannot be sold in the same month)
    m.addConstr(sell_1 <= initial_inventory, name="sell1_cap")
    m.addConstr(sell_2 <= inventory_1, name="sell2_cap")
    m.addConstr(sell_3 <= inventory_2, name="sell3_cap")

    # Capacity constraints (enforced via lb/ub on inventory vars already)
    m.addConstr(inventory_1 <= capacity, name="cap1")
    m.addConstr(inventory_2 <= capacity, name="cap2")
    m.addConstr(inventory_3 <= capacity, name="cap3")

    # Cash flow constraints
    m.addConstr(cash_1 == initial_cash - buy_1 * p1 + sell_1 * sp1, name="cash1_calc")
    m.addConstr(cash_2 == cash_1 - buy_2 * p2 + sell_2 * sp2, name="cash2_calc")
    m.addConstr(cash_3 == cash_2 - buy_3 * p3 + sell_3 * sp3, name="cash3_calc")

    m.addConstr(cash_1 >= 0, name="cash1_nonneg")
    m.addConstr(cash_2 >= 0, name="cash2_nonneg")
    m.addConstr(cash_3 >= 0, name="cash3_nonneg")

    # Profit definition
    m.addConstr(profit == (sell_1 * sp1 + sell_2 * sp2 + sell_3 * sp3)
                        - (buy_1 * p1 + buy_2 * p2 + buy_3 * p3),
                name="profit_def")

    # Objective
    m.setObjective(profit, GRB.MAXIMIZE)

    # Return model and a dict of variable references with exact keys
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

    # Map status to a readable string
    status_code = model.Status
    if status_code == GRB.OPTIMAL:
        status = "OPTIMAL"
    elif status_code == GRB.INFEASIBLE:
        status = "INFEASIBLE"
    elif status_code == GRB.UNBOUNDED:
        status = "UNBOUNDED"
    elif status_code == GRB.INF_OR_UNBD:
        status = "INF_OR_UNBD"
    elif status_code == GRB.TIME_LIMIT:
        status = "TIME_LIMIT"
    else:
        status = str(status_code)

    objective_value = float(model.ObjVal) if model.ObjVal is not None else None

    # Read solution values
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
        "status": status,
        "objective": objective_value,
        "solution": solution
    }