import os
from mistralai import Mistral
from dotenv import load_dotenv

load_dotenv()

def test_mistral_direct():
    api_key = os.getenv("MISTRAL_API_KEY")
    print(f"Testing Mistral with key: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")
    
    try:
        with Mistral(api_key=api_key) as mistral:
            res = mistral.chat.complete(
                model="mistral-small-latest",
                messages=[
                    {"role": "user", "content": "Say 'Mistral is working' if you can read this."}
                ]
            )
            print(f"Response: {res.choices[0].message.content}")
            return True
    except Exception as e:
        print(f"Mistral Error: {e}")
        return False

if __name__ == "__main__":
    test_mistral_direct()
