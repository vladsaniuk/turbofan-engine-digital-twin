import os
import sys

def check_gemini_api():
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("GEMINI_API_KEY is not set. Please set the environment variable and try again.")
        sys.exit(0)
    
    try:
        from google import genai
        client = genai.Client()
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents='reply OK if you can read this',
            config=genai.types.GenerateContentConfig(
                max_output_tokens=50,
            )
        )
        print("API Response:", response.text)
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        sys.exit(0)

if __name__ == "__main__":
    check_gemini_api()
