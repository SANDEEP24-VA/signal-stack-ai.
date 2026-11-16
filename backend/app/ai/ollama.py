import logging
from typing import Optional
import httpx
from app.ai.base import AICompletionResult, BaseAIProvider

logger = logging.getLogger(__name__)


class OllamaProvider(BaseAIProvider):
    """Local Ollama AI Provider implementation."""

    def __init__(self, base_url: str = "http://localhost:11434", model_name: str = "llama3.2"):
        super().__init__(model_name=model_name)
        self.base_url = base_url.rstrip("/")

    async def is_available(self) -> bool:
        """Check if Ollama daemon is reachable and whether the model or tags respond."""
        try:
            async with httpx.AsyncClient(timeout=3.0) as client:
                res = await client.get(f"{self.base_url}/api/tags")
                if res.status_code != 200:
                    return False
                data = res.json()
                models = [m.get("name", "") for m in data.get("models", [])]
                # Match e.g. "llama3.2" against "llama3.2:latest"
                for m in models:
                    if m == self.model_name or m.startswith(f"{self.model_name}:") or self.model_name.startswith(m):
                        return True
                # If tags endpoint works but model name differs, Ollama is still reachable
                return len(models) > 0
        except Exception as e:
            logger.debug(f"Ollama availability check failed: {e}")
            return False

    async def generate_completion(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AICompletionResult:
        """Generate completion using Ollama /api/generate endpoint with JSON formatting."""
        if not await self.is_available():
            raise ConnectionError(f"Ollama server is unreachable at {self.base_url} or model is missing.")

        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "format": "json",
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }
        if system_instruction:
            payload["system"] = system_instruction

        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                res = await client.post(f"{self.base_url}/api/generate", json=payload)
                res.raise_for_status()
                data = res.json()
                raw_text = data.get("response", "")
                return AICompletionResult(
                    raw_text=raw_text,
                    model=data.get("model", self.model_name),
                    provider="ollama",
                    metadata={
                        "total_duration": data.get("total_duration"),
                        "eval_count": data.get("eval_count"),
                    },
                )
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Ollama API returned HTTP {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to communicate with Ollama at {self.base_url}: {e}")
