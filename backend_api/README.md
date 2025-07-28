# Backend API Deployment

This document provides instructions on how to deploy the TikTok Comments Crawler backend API.

## 1. Prerequisites

- Python 3.8+
- `pip` for package management

## 2. Installation

1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd insight_analysis/backend_api
    ```

2.  **Create and activate a virtual environment (recommended):**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

## 3. Configuration

1.  **Set the Gemini API Key:**
    The application uses the Gemini API for comment analysis. You need to provide your API key as an environment variable.

    ```bash
    export GEMINI_API_KEY="your_gemini_api_key_here"
    ```

    If you don't set this key, the server will still run, but the analysis endpoints will be disabled.

## 4. Running the Server

Once the dependencies are installed and the API key is configured, you can start the server:

```bash
python start_server.py
```

The server will be running at `http://0.0.0.0:8000`.

## 5. API Documentation

You can access the interactive API documentation (Swagger UI) at:

`http://localhost:8000/docs` 