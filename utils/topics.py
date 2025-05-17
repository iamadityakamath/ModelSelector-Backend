from google import genai
from google.genai import types
from router_prompt import Topic_Pompt
import json
def get_topics(client,user_input,MODEL):
    response = client.models.generate_content(
                model=MODEL, 
                config=types.GenerateContentConfig(system_instruction=Topic_Pompt, response_mime_type="application/json"),
                contents=json.dumps(user_input)
                )
                
    parsed_output = json.loads(response.text)
    topic = parsed_output.get("Topic", "").lower()
    return topic