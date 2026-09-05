import gurobipy as gp
from gurobipy import GRB

def build_model(data: dict) -> tuple:
    # Prepare data
    veg_oils = data["vegetable_oils"]
    nonveg_oils = data["non_vegetable_oils"]
    oils = veg_oils + nonveg_oils
    months = data["months"]

    m = gp.Model()

    storage_cap = data["storage_cap_per_oil"]
    storage_cost = data["storage_cost_per_ton_month"]
    initial_storage = data["initial_storage_per_oil"]
    final_storage_needed = data["required_final_storage_per_oil"]
    sell_price = data["sell_price"]
    veg_cap = data["veg_refine_cap"]
    nonveg_cap = data["nonveg_refine_cap"]
    purchase_price = data["purchase_price"]

    hardness = data["hardness"]

    # Create decision variables
    # We'll store all variables in a flat dict keyed by exact names
    variables = {}

    buy = {}
    use = {}
    store = {}
    y = {}

    for oil in oils:
        buy[oil] = {}
        use[oil] = {}
        store[oil] = {}
        y[oil] = {}
        for month in months:
            v_buy = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"buy_{oil}_{month}")
            v_use = m.addVar(lb=0.0, vtype=GRB.CONTINUOUS, name=f"use_{oil}_{month}")
            v_store = m.addVar(lb=0.0, ub=storage_cap, vtype=GRB.CONTINUOUS, name=f"store_{oil}_{month}")
            v_y = m.addVar(vtype=GRB.BINARY, name=f"y_{oil}_{month}")

            buy[oil][month] = v_buy
            use[oil][month] = v_use
            store[oil][month] = v_store
            y[oil][month] = v_y

            variables[f"buy_{oil}_{month}"] = v_buy
            variables[f"use_{oil}_{month}"] = v_use
            variables[f"store_{oil}_{month}"] = v_store
            variables[f"y_{oil}_{month}"] = v_y

    # Objective: maximize revenue from final product minus purchasing costs minus storage costs
    obj = gp.LinExpr()
    for oil in oils:
        for month in months:
            price = purchase_price[month][oil]
            obj += sell_price * use[oil][month] - price * buy[oil][month] - storage_cost * store[oil][month]
    m.setObjective(obj, GRB.MAXIMIZE)

    # Constraints

    # Flow balance for storage (inventory balance)
    for oil in oils:
        # January balance
        m.addConstr(store[oil]["Jan"] == initial_storage + buy[oil]["Jan"] - use[oil]["Jan"], name=f"bal_{oil}_Jan")
        # February to June balances
        for idx in range(1, len(months)):
            month = months[idx]
            prev = months[idx - 1]
            m.addConstr(store[oil][month] - store[oil][prev] == buy[oil][month] - use[oil][month],
                        name=f"bal_{oil}_{month}")

    # Final storage constraints: must remain at end of June
    for oil in oils:
        m.addConstr(store[oil]["Jun"] == final_storage_needed, name=f"final_store_{oil}")

    # Refining capacity per month
    for month in months:
        m.addConstr(use["VEG1"][month] + use["VEG2"][month] <= veg_cap, name=f"veg_cap_{month}")
        m.addConstr(use["OIL1"][month] + use["OIL2"][month] + use["OIL3"][month] <= nonveg_cap,
                    name=f"nonveg_cap_{month}")

    # At most three oils used per month (by y variables)
    for month in months:
        m.addConstr(y["VEG1"][month] + y["VEG2"][month] + y["OIL1"][month] + y["OIL2"][month] + y["OIL3"][month] <= 3,
                    name=f"three_oils_{month}")

    # If an oil is used, at least 20 tons must be used
    BIGM = 10**6
    for oil in oils:
        for month in months:
            m.addConstr(use[oil][month] >= 20 * y[oil][month], name=f"min_use_{oil}_{month}")
            m.addConstr(use[oil][month] <= BIGM * y[oil][month], name=f"use_if_used_{oil}_{month}")

    # If VEG1 or VEG2 is used, OIL3 must also be used
    for month in months:
        m.addConstr(y["VEG1"][month] <= y["OIL3"][month], name=f"veg1_requires_oil3_{month}")
        m.addConstr(y["VEG2"][month] <= y["OIL3"][month], name=f"veg2_requires_oil3_{month}")

    # Add to model
    m.update()
    return m, variables

def solve(data: dict) -> dict:
    model, variables = build_model(data)

    # Optimize
    model.optimize()
    model.update()

    # Status string mapping
    status_map = {
        GRB.OPTIMAL: "OPTIMAL",
        GRB.INFEASIBLE: "INFEASIBLE",
        GRB.UNBOUNDED: "UNBOUNDED",
        GRB.INF_OR_UNBD: "INF_OR_UNBD",
        GRB.TIME_LIMIT: "TIME_LIMIT"
    }
    st = model.Status
    status = status_map.get(st, str(st))

    # Objective value
    objective = float(model.ObjVal)

    # Build solution dictionary with all variable values
    solution = {}
    for key, var in variables.items():
        solution[key] = float(var.X)

    return {
        "type": "object",
        "status": status,
        "objective": objective,
        "solution": solution
    }