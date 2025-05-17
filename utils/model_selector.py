import json
import time
from google.genai import types
from flask import jsonify # Keep jsonify for potential error returns, though returning data is often cleaner

# Consider adding logging here if needed

def get_model_response(client, messages, model_name, system_prompt):
    """Interacts with the generative model in a loop to get a final response.

    Args:
        client: The initialized Google GenAI client.
        messages: A list of message dictionaries representing the conversation history.
        model_name: The name of the model to use.
        system_prompt: The system prompt string.

    Returns:
        A tuple containing:
        - final_response_content (str or None): The content of the final 'output' step.
        - thinking_steps (list): A list of thoughts from 'plan' or 'think' steps.
        - error (str or None): An error message if an exception occurred.
        - status_code (int): HTTP status code (relevant if an error occurred).
    """
    final_response_content = None
    thinking_steps = []
    counter = 0
    max_steps = 3 # Limit the interaction steps

    while counter < max_steps:
        counter += 1
        # print(f"Step: {counter}") # Server-side logging (optional)

        try:
            response = client.models.generate_content(
                model=model_name,
                config=types.GenerateContentConfig(system_instruction=system_prompt, response_mime_type="application/json"),
                contents=json.dumps(messages) # Pass the current message history
            )

            if not hasattr(response, 'text') or not response.text:
                print("Warning: Response has no text attribute or is empty.")
                return None, thinking_steps, "Received empty response from model", 500

            try:
                parsed_output = json.loads(response.text)
            except json.JSONDecodeError as e:
                print(f"Error decoding JSON response: {e}")
                print(f"Raw response text: {response.text}")
                return None, thinking_steps, f"Failed to decode model response: {e}", 500

            # Append the raw assistant response to the history for the next turn
            messages.append({ "role": "assistant", "content": json.dumps(parsed_output) })

            step_type = parsed_output.get("step", "").lower()

            if step_type in ["plan", "think"]:
                thought = parsed_output.get('content', 'No content in thought step.')
                # print(f"🧠: {thought}") # Server-side logging (optional)
                thinking_steps.append(thought)
                continue # Go to the next iteration

            if step_type == "output":
                final_response_content = parsed_output.get('content', 'No content in output step.')
                # print(f"🤖: {final_response_content}") # Server-side logging (optional)
                break # Exit loop, we have the final answer

            # Handle unexpected step types if necessary
            print(f"Unknown or intermediate step '{step_type}': {parsed_output.get('content')}")
            # Decide if unknown steps should halt the process or be logged
            # thinking_steps.append(f"Unknown step '{step_type}': {parsed_output.get('content')}") # Optionally log unknown steps

        except Exception as e:
            print(f"An error occurred during content generation: {e}")
            # import traceback; traceback.print_exc() # Uncomment for detailed traceback
            return None, thinking_steps, f"An unexpected error occurred: {e}", 500

    # Return results after the loop finishes (either by break or max_steps)
    return final_response_content, thinking_steps, None, 200