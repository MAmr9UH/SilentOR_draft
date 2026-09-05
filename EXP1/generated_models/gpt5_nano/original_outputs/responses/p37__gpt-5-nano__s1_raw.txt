import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict):
    model = gp.Model()
    model.Params.OutputFlag = 0

    # Parameters from data
    I0 = data.get("initial_inventory", 0)
    C0 = data.get("initial_cash", 0)
    cap = data.get("capacity", 0)
    final_inv = data.get("final_inventory_required", 0)

    purchase_price = {t: float(data["purchase_price"][str(t)]) for t in (1, 2, 3)}
    selling_price = {t: float(data["selling_price"][str(t)]) for t in (1, 2, 3)}

    # Decision variables
    buy_1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="buy_1")
    buy_2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="buy_2")
    buy_3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="buy_3")

    sell_1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="sell_1")
    sell_2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="sell_2")
    sell_3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="sell_3")

    inventory_1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="inventory_1")
    inventory_2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="inventory_2")
    inventory_3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="inventory_3")

    cash_1 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_1")
    cash_2 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_2")
    cash_3 = model.addVar(lb=0, vtype=GRB.CONTINUOUS, name="cash_3")

    profit = model.addVar(lb=-GRB.INFINITY, vtype=GRB.CONTINUOUS, name="profit")

    # Constraints
    # Inventory balance
    model.addConstr(inventory_1 == I0 + buy_1 - sell_1, name="inv1")
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2, name="inv2")
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3, name="inv3")

    # Capacity constraints
    model.addConstr(inventory_1 <= cap, name="cap1")
    model.addConstr(inventory_2 <= cap, name="cap2")
    model.addConstr(inventory_3 <= cap, name="cap3")

    # Sell constraints (only sellable next month)
    model.addConstr(sell_1 <= I0, name="sell1_cap")
    model.addConstr(sell_2 <= inventory_1, name="sell2_cap")
    model.addConstr(sell_3 <= inventory_2, name="sell3_cap")

    # Cash balance
    model.addConstr(cash_1 == C0 - buy_1 * purchase_price[1] + sell_1 * selling_price[1], name="cash1")
    model.addConstr(cash_2 == cash_1 - buy_2 * purchase_price[2] + sell_2 * selling_price[2], name="cash2")
    model.addConstr(cash_3 == cash_2 - buy_3 * purchase_price[3] + sell_3 * selling_price[3], name="cash3")

    # End inventory requirement
    model.addConstr(inventory_3 == final_inv, name="final_inv")

    # Profit definition
    profit_expr = quicksum([sell_1 * selling_price[1], sell_2 * selling_price[2], sell_3 * selling_price[3]]) \
                  - quicksum([buy_1 * purchase_price[1], buy_2 * purchase_price[2], buy_3 * purchase_price[3]])
    model.addConstr(profit == profit_expr, name="profit_eq")

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

    status = model.Status
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.TIME_LIMIT: "TIME_LIMIT",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD"
    }
    status_str = status_map.get(status, str(status))

    solution = {k: float(variables[k].X) for k in [
        "buy_1", "buy_2", "buy_3",
        "sell_1", "sell_2", "sell_3",
        "inventory_1", "inventory_2", "inventory_3",
        "cash_1", "cash_2", "cash_3",
        "profit"
    ]}

    return {
        "type": "object",
        "status": status_str,
        "objective": float(model.ObjVal),
        "solution": solution
    }