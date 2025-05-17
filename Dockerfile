# Use an official Python runtime as a parent image
FROM python:3.11-slim

WORKDIR /app

# Copy the requirements file into the container at /app
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application code into the container at /app
# Ensure all necessary files and directories are copied
COPY main.py .
COPY router_prompt.py .
COPY utils/ ./utils/
EXPOSE 5000

CMD ["python", "main.py"]