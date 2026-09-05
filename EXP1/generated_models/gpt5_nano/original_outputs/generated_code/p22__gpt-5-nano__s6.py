import gurobipy as gp
from gurobipy import GRB, quicksum

def build_model(data: dict) -> tuple:
    nodes = data["nodes"]
    source = data["source"]
    sink = data["sink"]
    required_service_node = data["required_service_node"]