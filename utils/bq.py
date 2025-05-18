import os
from datetime import datetime
from google.cloud import bigquery
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

# Removed: from google.oauth2 import service_account

def initialize_bq_client():
    """Initializes the BigQuery client and table reference.

    Reads necessary environment variables (PROJECT_ID, DATASET_ID, TABLE_ID)
    and uses a service account key for authentication.

    Returns:
        tuple: (bigquery.Client or None, bigquery.TableReference or None)
               Returns (None, None) if configuration is incomplete or an error occurs.
    """
    try:
        BIGQUERY_PROJECT_ID = os.environ.get("BIGQUERY_PROJECT_ID")
        BIGQUERY_DATASET_ID = os.environ.get("BIGQUERY_DATASET_ID")
        BIGQUERY_TABLE_ID = os.environ.get("BIGQUERY_TABLE_ID")
        # Removed: SERVICE_ACCOUNT_FILE = os.path.join(os.path.dirname(__file__), '..', 'service_account_key.json')

        if not all([BIGQUERY_PROJECT_ID, BIGQUERY_DATASET_ID, BIGQUERY_TABLE_ID]):
            print("Warning: BigQuery environment variables (PROJECT_ID, DATASET_ID, TABLE_ID) not fully set. BigQuery logging disabled.")
            return None, None

        # Removed: Service account file check and loading
        # The client will now use Application Default Credentials
        client = bigquery.Client(project=BIGQUERY_PROJECT_ID)
        table_ref = client.dataset(BIGQUERY_DATASET_ID).table(BIGQUERY_TABLE_ID)
        print(f"BigQuery client initialized using default credentials for table: {BIGQUERY_PROJECT_ID}.{BIGQUERY_DATASET_ID}.{BIGQUERY_TABLE_ID}")
        return client, table_ref

    except Exception as e:
        print(f"Error initializing Google BigQuery client: {e}")
        return None, None

def log_to_bigquery(client, table_ref, log_data):
    """Logs data to the specified BigQuery table.

    Args:
        client (bigquery.Client): The initialized BigQuery client.
        table_ref (bigquery.TableReference): The reference to the target table.
        log_data (dict): The dictionary containing the data to log.
    """
    if not client or not table_ref:
        print("BigQuery client not available. Skipping logging.")
        return

    try:
        rows_to_insert = [log_data]
        errors = client.insert_rows_json(table_ref, rows_to_insert)
        if errors:
            print(f"Encountered errors while inserting rows into BigQuery: {errors}")
            # Consider more robust error handling if needed
        else:
            print("Successfully logged data to BigQuery.")
    except Exception as e:
        print(f"Error logging data to BigQuery: {e}")
        # Decide if this error should be raised or handled differently