import operator
from typing import Annotated, Any
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, START, END

class State(TypedDict):
    val: Annotated[int, operator.add]
    steps: Annotated[list[str], operator.add]

def node_a(state: State):
    return {"val": 1, "steps": ["A"]}

def node_b(state: State):
    return {"val": 2, "steps": ["B"]}

def node_c(state: State):
    return {"val": 0, "steps": ["C"]}

def route(state: State) -> Any:
    if state["val"] == 0:
        return ["A", "B"]
    return "C"

builder = StateGraph(State)
builder.add_node("A", node_a)
builder.add_node("B", node_b)
builder.add_node("C", node_c)

builder.add_conditional_edges(START, route, {"A": "A", "B": "B", "C": "C"})
builder.add_edge("A", "C")
builder.add_edge("B", "C")

app = builder.compile()

if __name__ == "__main__":
    print(app.invoke({"val": 0, "steps": []}))
    print(app.invoke({"val": 10, "steps": []}))
