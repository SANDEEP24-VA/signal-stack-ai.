import logging
from typing import Optional
import httpx
from app.ai.base import AICompletionResult, BaseAIProvider

logger = logging.getLogger(__name__)


class GeminiProvider(BaseAIProvider):
    """Google Gemini AI Provider implementation via REST API."""

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-1.5-flash"):
        super().__init__(model_name=model_name)
        self.api_key = api_key

    async def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 0)

    async def generate_completion(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AICompletionResult:
        if not await self.is_available():
            raise ValueError("Gemini API key is not configured. Set GEMINI_API_KEY in .env.")

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"

        contents = [{"parts": [{"text": prompt}]}]
        body = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "responseMimeType": "application/json",
            },
        }
        if system_instruction:
            body["systemInstruction"] = {"parts": [{"text": system_instruction}]}

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                res = await client.post(url, json=body)
                res.raise_for_status()
                data = res.json()
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("Gemini returned empty candidates")

                text_part = candidates[0].get("content", {}).get("parts", [{}])[0].get("text", "")
                return AICompletionResult(
                    raw_text=text_part,
                    model=self.model_name,
                    provider="gemini",
                    metadata={"usageMetadata": data.get("usageMetadata")},
                )
            except httpx.HTTPStatusError as e:
                raise RuntimeError(f"Gemini API returned HTTP {e.response.status_code}: {e.response.text}")
            except httpx.RequestError as e:
                raise ConnectionError(f"Failed to connect to Google Gemini API: {e}")
