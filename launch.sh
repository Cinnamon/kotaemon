#!/bin/bash

if [ -z "$GRADIO_SERVER_NAME" ]; then
    export GRADIO_SERVER_NAME="0.0.0.0"
fi
if [ -z "$GRADIO_SERVER_PORT" ]; then
    export GRADIO_SERVER_PORT="7860"
fi

# Check if environment variable KH_DEMO_MODE is set to true
if [ "$KH_DEMO_MODE" = "true" ]; then
    echo "KH_DEMO_MODE is true. Launching in demo mode..."
    # Command to launch in demo mode
    GR_FILE_ROOT_PATH="/app" KH_FEATURE_USER_MANAGEMENT=false USE_LIGHTRAG=false uvicorn sso_app_demo:app --host "$GRADIO_SERVER_NAME" --port "$GRADIO_SERVER_PORT"
else
    if [ "$KH_SSO_ENABLED" = "true" ]; then
        echo "KH_SSO_ENABLED is true. Launching in SSO mode..."
        GR_FILE_ROOT_PATH="/app" KH_SSO_ENABLED=true uvicorn sso_app:app --host "$GRADIO_SERVER_NAME" --port "$GRADIO_SERVER_PORT"
    else
        ollama serve &
        python app.py
    fi
fi
