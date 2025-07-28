# Use an official Python runtime as a parent image
FROM python:3.10-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file from the backend_api directory
COPY backend_api/requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project context into the container.
# This makes both backend_api/ and TikTok_CMT/ available inside the container.
COPY . .

# Make port 8000 available to the world outside this container
EXPOSE 8000

# Run main.py from the backend_api directory when the container launches
CMD ["uvicorn", "backend_api.main:app", "--host", "0.0.0.0", "--port", "8000"] 