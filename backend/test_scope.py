import os
from sql_agent import run_nlp_to_sql
from dotenv import load_dotenv

load_dotenv()

def test_out_of_scope():
    queries = [
        "give me employee details working in US",
        "who are the top 5 customers?" # Should match
    ]
    
    for q in queries:
        print(f"\n--- Testing Query: {q} ---")
        result = run_nlp_to_sql(q, verbose=True)
        print(f"\n--- FINAL WRAPPED OUTPUT ---")
        print(f"Success: {result['success']}")
        if result['success']:
            print(f"SQL: {result['sql']}")
            print(f"Category: {result.get('category')}")
        else:
            print(f"Error: {result.get('error')}")

if __name__ == "__main__":
    test_out_of_scope()
