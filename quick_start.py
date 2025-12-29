"""
Quick start script to test the Multi-Agent NLP-to-SQL System

This script demonstrates basic usage with a few example queries.
"""

import os
from sql_agent import run_nlp_to_sql

def main():
    # Check for API key
    if not os.getenv("GROQ_API_KEY"):
        print("❌ Error: GROQ_API_KEY not set!")
        print("\nPlease set your Groq API key:")
        print("  Windows: $env:GROQ_API_KEY='your-key'")
        print("  Linux/Mac: export GROQ_API_KEY='your-key'")
        print("\nGet your free API key at: https://console.groq.com")
        return
    
    print("🚀 Multi-Agent NLP-to-SQL System - Quick Start\n")
    
    # Example queries
    queries = [
        "Show me the top 5 customers by total spending",
        "What products are currently out of stock?",
        "List orders from the last week that are still pending"
    ]
    
    for i, query in enumerate(queries, 1):
        print(f"\n{'='*70}")
        print(f"Query {i}: {query}")
        print('='*70)
        
        result = run_nlp_to_sql(query, verbose=True)
        
        if result["success"]:
            print(f"\n✅ Success!")
            print(f"📂 Category: {result['category']}")
            print(f"🎯 Accuracy: {result['evaluation']['accuracy_score']:.2f}")
        else:
            print(f"\n❌ Failed: {result['error']}")
        
        print("\n" + "="*70)
        
        # Pause between queries
        if i < len(queries):
            input("\nPress Enter to continue to next query...")
    
    print("\n✨ Quick start complete!")
    print("\nTo run more tests, execute: python sql_agent.py")

if __name__ == "__main__":
    main()
