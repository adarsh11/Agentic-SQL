import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

def test_groq_direct():
    api_key = os.getenv("GROQ_API_KEY")
    base_url = "https://api.groq.com/openai/v1"
    model = "moonshotai/kimi-k2-instruct-0905"
    
    print(f"Testing Groq with key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    try:
        client = OpenAI(api_key=api_key, base_url=base_url)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Say 'Groq is working' if you can read this."}
            ]
        )
        print(f"Response: {response.choices[0].message.content}")
        return True
    except Exception as e:
        print(f"Groq Error: {e}")
        return False

if __name__ == "__main__":
    test_groq_direct()
