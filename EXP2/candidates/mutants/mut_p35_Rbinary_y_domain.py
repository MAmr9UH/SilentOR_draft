"""Certified base model for Exp-2 problem 35 (fixed_charge_two_station_transshipment_mip).
Two sources -> two stations -> two demands, with per-station fixed cost + capacity, activated
only if the station-use binary is on. Returns keys x_i_k, z_k_j, y_k."""
import gurobipy as gp
from gurobipy import GRB


def build_model(data: dict) -> tuple:
    S = data["sources"]; K = data["stations"]; D = data["demands"]
    supply = data["supply"]; demand = data["demand"]
    cap = data["station_capacity"]; fixed = data["fixed_cost"]
    csk = data["cost_source_station"]; ckd = data["cost_station_demand"]
    m = gp.Model(); m.Params.OutputFlag = 0

    x = {(i, k): m.addVar(lb=0, name=f"x_{i}_{k}") for i in S for k in K}   # source->station
    z = {(k, j): m.addVar(lb=0, name=f"z_{k}_{j}") for k in K for j in D}   # station->demand
    y = {k: m.addVar(lb=0, ub=1, name=f"y_{k}") for k in K}                 # station use

    # R_supply_i: leaving source i <= supply
    for i in S:
        m.addConstr(gp.quicksum(x[(i, k)] for k in K) <= supply[i], name=f"supply_{i}")
    # R_demand_j: delivered to j == demand (exact)
    for j in D:
        m.addConstr(gp.quicksum(z[(k, j)] for k in K) == demand[j], name=f"demand_{j}")
    # R_balance_station_k: flow in == flow out
    for k in K:
        m.addConstr(gp.quicksum(x[(i, k)] for i in S) == gp.quicksum(z[(k, j)] for j in D),
                    name=f"balance_{k}")
    # R_capacity_link_station_k: throughput <= cap * y_k  (fixed-charge link + capacity)
    for k in K:
        m.addConstr(gp.quicksum(x[(i, k)] for i in S) <= cap[k] * y[k], name=f"caplink_{k}")

    # R_obj: source->station transport + station->demand transport + fixed station cost
    m.setObjective(
        gp.quicksum(csk[f"{i},{k}"] * x[(i, k)] for i in S for k in K)
        + gp.quicksum(ckd[f"{k},{j}"] * z[(k, j)] for k in K for j in D)
        + gp.quicksum(fixed[k] * y[k] for k in K), GRB.MINIMIZE)

    variables = {}
    for (i, k), v in x.items():
        variables[f"x_{i}_{k}"] = v
    for (k, j), v in z.items():
        variables[f"z_{k}_{j}"] = v
    for k, v in y.items():
        variables[f"y_{k}"] = v
    return m, variables


def solve(data: dict) -> dict:
    m, variables = build_model(data)
    m.optimize()
    status_map = {GRB.OPTIMAL: "OPTIMAL", GRB.INFEASIBLE: "INFEASIBLE",
                  GRB.UNBOUNDED: "UNBOUNDED", GRB.INF_OR_UNBD: "INF_OR_UNBD",
                  GRB.TIME_LIMIT: "TIME_LIMIT"}
    sol = {}
    for key, v in variables.items():
        val = v.X
        sol[key] = int(round(val)) if key.startswith("y_") else float(val)
    return {"status": status_map.get(m.Status, str(m.Status)),
            "objective": float(m.ObjVal), "solution": sol}
