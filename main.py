from flask import Flask, request, jsonify
from dotenv import load_dotenv
import os
from google import genai
from google.genai import types
import requests # Although requests is imported, it's not used in the provided snippet. Keep if needed elsewhere.
import json
import time
from flask_cors import CORS # Import the CORS extension
from langfuse import Langfuse
from langfuse.decorators import observe,langfuse_context
from datetime import datetime # Add datetime import
# BigQuery import moved to utils/bq.py
from utils.bq import initialize_bq_client, log_to_bigquery # Import BQ utils
from langfuse import Langfuse
from router_prompt import system_prompt, Examples # task_examples is imported but not used
from utils.topics import get_topics
from utils.model_selector import get_model_response # Import the new function
load_dotenv()
MODEL = os.getenv("MODEL")
# Initialize Flask app
app = Flask(__name__)
CORS(app, resources={r"/chat": {"origins": "http://localhost:5173","https://modelselector-backend-1051022814597.us-central1.run.app"}})

# Initialize Google GenAI Client
try:
    # Using the client structure from your original script
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    if not os.getenv("GEMINI_API_KEY"):
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
except Exception as e:
    print(f"Error initializing Google GenAI client: {e}")
    # Handle the error appropriately, maybe exit or disable the related endpoint
    client = None

# Initialize Google BigQuery Client using utility function
bigquery_client, table_ref = initialize_bq_client()


@app.route('/chat', methods=['POST'])
@observe()
def chat():
    
    if not client:
        return jsonify({"error": "GenAI client not initialized"}), 500

    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({"error": "Missing 'query' in request body"}), 400

    user_query = data['query'] # Get user query from request
    langfuse_context.update_current_trace(
        session_id=data['sessionId']
    )
    # --- Start of model interaction ---
    messages = [
        { "role": "system", "content": system_prompt + Examples}
    ]
    messages.append({ "role": "user", "content": user_query })

    start_time = time.time() # Start time for measuring duration

    # Call the utility function to handle model interaction
    final_response_content, thinking_steps, error_message, status_code = get_model_response(
        client=client,
        messages=messages, # Pass the current messages list
        model_name=MODEL,
        system_prompt=system_prompt
    )

    endtime = time.time() - start_time # Calculate duration

    # Handle potential errors from the model interaction function
    if error_message:
        return jsonify({"error": error_message}), status_code

    # Get topics after successful interaction (or decide if it should be before)
    # Note: get_topics might need adjustment if it relies on the 'messages' list *during* the interaction loop
    topics = get_topics(client, { "role": "user", "content": user_query }, MODEL)

    # --- End of model interaction ---

    # --- BigQuery Logging ---
    bq_log_data = {
        "timestamp": datetime.utcnow().isoformat(), # Use ISO format for BQ TIMESTAMP
        "session_id": data.get('sessionId', None), # Get session ID if available
        "user_query": user_query,
        "final_response": final_response_content,
        "plan_step": thinking_steps[0] if len(thinking_steps) > 0 else None,
        "think_step": thinking_steps[1] if len(thinking_steps) > 1 else None,
        "duration": endtime,
        "model_used": MODEL,
        "topic": topics,
        # Add other relevant fields from the request or response as needed
        # "model_used": MODEL, # Example
    }

    # Log using the utility function
    log_to_bigquery(bigquery_client, table_ref, bq_log_data)

    # --- End of BigQuery Logging ---

    # Return the final result or indicate if no output step was reached
    if final_response_content is not None:
        return jsonify({
            "response": final_response_content,
            "Plan": thinking_steps[0] if len(thinking_steps) > 0 else "N/A", # Handle potential index error
            "Think": thinking_steps[1] if len(thinking_steps) > 1 else "N/A" # Handle potential index error
        })
    else:
        # Handle cases where the loop finished without a final 'output' step
        # Log this error case to BigQuery as well
        error_log_data = bq_log_data.copy() # Start with base data
        error_log_data["final_response"] = None # Indicate no final response
        error_log_data["error_message"] = "Failed to get a final output after maximum steps."
        log_to_bigquery(bigquery_client, table_ref, error_log_data)

        return jsonify({
            "error": "Failed to get a final output after maximum steps.",
            "thinking_steps": thinking_steps
        }), 500


@app.route('/health_check', methods=['GET'])
@observe()
def health_check():
    print("health-check logged")
    return "Success"

if __name__ == '__main__':
    # Runs the development server. For production, use a WSGI server like Gunicorn or Waitress.
    app.run(debug=True, host='0.0.0.0', port=5000) # debug=True enables auto-reloading and detailed error pages