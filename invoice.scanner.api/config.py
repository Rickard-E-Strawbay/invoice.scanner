# config.py
# Centralized settings for model_provider and other app-wide config

import os

GOOGLE_SEARCH_API_KEY = "AIzaSyDdn9EvB846XjoFRrIxbtJVt_p3GwX5O0E"
GOOGLE_SEARCH_ENGINE_ID = "970ef8a11e74a4ad4"
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "YOUR_OPENAI_API_KEY")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "YOUR_ANTHROPIC_API_KEY")
GEMINI_MODEL_NAME = "gemini-pro"
OPENAI_MODEL_NAME = "gpt-4o"
ANTHROPIC_MODEL_NAME = "claude-3.5-sonnet"
