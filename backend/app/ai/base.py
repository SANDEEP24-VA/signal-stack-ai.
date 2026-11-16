from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from pydantic import BaseModel


class AICompletionResult(BaseModel):
    raw_text: str
    model: str
    provider: str
    metadata: Dict[str, Any] = {}


class BaseAIProvider(ABC):
    """Abstract Base Class for AI model providers (Gemini, Ollama, etc.)."""

    def __init__(self, model_name: str):
        self.model_name = model_name

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if provider credentials or connection are valid."""
        pass

    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        temperature: float = 0.2,
    ) -> AICompletionResult:
        """Generate a text completion from the provider."""
        pass
