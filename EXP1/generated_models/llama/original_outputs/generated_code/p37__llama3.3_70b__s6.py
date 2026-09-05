import gurobipy as gp

def build_model(data: dict) -> tuple:
    model = gp.Model()
    
    buy_1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    buy_2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    buy_3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    sell_1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    sell_2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    sell_3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    inventory_1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    inventory_2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    inventory_3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    cash_1 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    cash_2 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    cash_3 = model.addVar(lb=0, vtype=gp.GRB.CONTINUOUS)
    
    profit = model.addVar(vtype=gp.GRB.CONTINUOUS)
    
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
    
    model.addConstr(inventory_1 == data["initial_inventory"] + buy_1 - sell_1)
    model.addConstr(inventory_2 == inventory_1 + buy_2 - sell_2)
    model.addConstr(inventory_3 == inventory_2 + buy_3 - sell_3)
    
    model.addConstr(cash_1 == data["initial_cash"] - buy_1 * data["purchase_price"]["1"])
    model.addConstr(cash_2 == cash_1 + sell_1 * data["selling_price"]["1"] - buy_2 * data["purchase_price"]["2"])
    model.addConstr(cash_3 == cash_2 + sell_2 * data["selling_price"]["2"] - buy_3 * data["purchase_price"]["3"])
    
    model.addConstr(inventory_1 <= data["capacity"])
    model.addConstr(inventory_2 <= data["capacity"])
    model.addConstr(inventory_3 == data["final_inventory_required"])
    
    model.addConstr(sell_1 <= buy_1)
    model.addConstr(sell_2 <= inventory_1 + buy_2 - sell_1)
    model.addConstr(sell_3 <= inventory_2 + buy_3 - sell_2)
    
    profit_expr = (sell_1 * data["selling_price"]["1"] +
                   sell_2 * data["selling_price"]["2"] +
                   sell_3 * data["selling_price"]["3] -
                   buy_1 * data["purchase_price"]["1"] -
                   buy_2 * data["purchase_price"]["2"] -
                   buy_3 * data["purchase_price"]["3"])
    model.addConstr(profit == profit_expr)
    
    model.setObjective(profit, gp.GRB.MAXIMIZE)
    
    return model, variables

def solve(data: dict) -> dict:
    model, _ = build_model(data)
    model.optimize()
    
    status_map = {
        gp.GRB.OPTIMAL: "OPTIMAL",
        gp.GRB.INFEASIBLE: "INFEASIBLE",
        gp.GRB.UNBOUNDED: "UNBOUNDED",
        gp.GRB.INF_OR_UNBD: "INF_OR_UNBD",
        gp.GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    
    solution = {
        "buy_1": model.getVarByName("buy_1").X,
        "buy_2": model.getVarByName("buy_2").X,
        "buy_3": model.getVarByName("buy_3").X,
        "sell_1": model.getVarByName("sell_1").X,
        "sell_2": model.getVarByName("sell_2").X,
        "sell_3": model.getVarByName("sell_3").X,
        "inventory_1": model.getVarByName("inventory_1").X,
        "inventory_2": model.getVarByName("inventory_2").X,
        "inventory_3": model.getVarByName("inventory_3").X,
        "cash_1": model.getVarByName("cash_1").X,
        "cash_2": model.getVarByName("cash_2").X,
        "cash_3": model.getVarByName("cash_3").X,
        "profit": model.getVarByName("profit").X
    }
    
    return {
        "status": status_map[model.Status],
        "objective": model.ObjVal,
        "solution": solution
    }