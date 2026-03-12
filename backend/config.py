import os
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

SUPERMEMORY_API_KEY = os.getenv("SUPERMEMORY_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
SUPERMEMORY_BASE_URL = "https://api.supermemory.ai/v3"
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "llama-3.3-70b-versatile"  # Fast, high quality reasoning
GEMINI_MODEL = "gemini-2.0-flash"
MAX_AGENT_STEPS = 10
STEP_DELAY = 2  # seconds between LLM calls (Groq is much faster, less delay needed)


