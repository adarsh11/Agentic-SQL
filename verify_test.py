import os
import sys
from sql_agent import run_nlp_to_sql

# Save original stdout
original_stdout = sys.stdout

# Redirect stdout to a file with utf-8 encoding
with open('test_output.log', 'w', encoding='utf-8') as f:
    sys.stdout = f
    
    print("Starting Multi-Agent SQL System Test...")
    print("="*50)

    test_cases = [
        "Who are the top 5 customers by total spending?",
        "Which products are currently low in stock?",
    ]

    for query in test_cases:
        print(f"\nQUERY: {query}")
        result = run_nlp_to_sql(query, verbose=True)
        if result["success"]:
            print("\nRESULT: SUCCESS")
            print(f"SQL:\n{result['sql']}")
        else:
            print(f"\nRESULT: FAILED - {result['error']}")
        print("-" * 50)

# Restore stdout
sys.stdout = original_stdout
print("Tests completed. Check test_output.log")
