import asyncio
import logging
from graph.builder import build_graph

logging.basicConfig(level=logging.INFO)

async def main():
    graph = build_graph()
    initial_state = {
        "user_query": "Top 5 ngành học có đông sinh viên nhất",
        "history": [],
    }
    
    async for output in graph.astream(initial_state):
        for node_name, state in output.items():
            print(f"--- Node: {node_name} ---")
            print("Intent:", state.get("intent"))
            if "executor_error" in state:
                print("Error:", state["executor_error"])
            if "answer" in state:
                print("Answer:", state["answer"])

asyncio.run(main())
