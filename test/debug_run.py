import asyncio
from graph.builder import build_graph
import uuid
import logging

logging.basicConfig(level=logging.INFO)

async def test_run():
    app = build_graph()
    test_query = "Cho tôi biết tổng doanh thu của công ty?"
    state = {
        "user_query": test_query,
        "session_id": str(uuid.uuid4()),
        "retry_count": 0
    }
    
    print(f"Testing Query: {test_query}")
    try:
        final_state = await app.ainvoke(state)
        print("\n--- Final State ---")
        print(f"Intent: {final_state.get('intent')}")
        print(f"SQL Plan:\n{final_state.get('query_plan')}")
        print(f"Generated SQL:\n{final_state.get('generated_sql')}")
        
        correction = final_state.get('sql_correction')
        if correction:
            print(f"Correction Result: isValid={correction.get('is_valid')}")
            print(f"Correction Issues: {correction.get('issues')}")
            
        print(f"Final Executed SQL:\n{final_state.get('final_sql')}")
        print(f"Final Answer:\n{final_state.get('answer')}")
    except Exception as e:
        print(f"Workflow failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_run())
