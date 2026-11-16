import logging
from typing import Optional
from app.ai.base import BaseAIProvider
from app.ai.gemini import GeminiProvider
from app.ai.ollama import OllamaProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


async def get_active_ai_provider() -> Optional[BaseAIProvider]:
    """
    Select and return an active, functioning AI provider.
    Prioritizes Ollama if available on localhost, then Gemini if configured.
    """
    settings = get_settings()

    # 1. Check Ollama first
    if settings.OLLAMA_BASE_URL:
        try:
            ollama = OllamaProvider(
                base_url=settings.OLLAMA_BASE_URL,
                model_name=settings.OLLAMA_MODEL,
            )
            if await ollama.is_available():
                logger.info(f"Using active Ollama AI provider ({settings.OLLAMA_MODEL}) at {settings.OLLAMA_BASE_URL}")
                return ollama
        except Exception as e:
            logger.debug(f"Ollama provider check failed: {e}")

    # 2. Check Gemini as compatible alternative
    if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
        try:
            gemini = GeminiProvider(
                api_key=settings.GEMINI_API_KEY,
                model_name=settings.GEMINI_MODEL,
            )
            if await gemini.is_available():
                logger.info(f"Using active Google Gemini AI provider ({settings.GEMINI_MODEL})")
                return gemini
        except Exception as e:
            logger.debug(f"Gemini provider check failed: {e}")

    logger.warning("No functioning AI provider is currently available.")
    return None
