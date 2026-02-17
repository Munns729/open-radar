
import logging
import aiohttp
import json
from typing import Dict, Any, Optional, List
from src.core.config import settings

logger = logging.getLogger(__name__)

class MoonshotClient:
    def __init__(self):
        self.api_key = settings.moonshot_api_key
        self.api_base = settings.kimi_api_base
        self.model = settings.kimi_model
        # Fallback if config is missing specific model, though config likely has kimi-latest
        
        if not self.api_key:
            logger.warning("MOONSHOT_API_KEY not set. AI features will fail or return mocks.")

    async def generate(self, prompt: str, system_prompt: str = "You are a helpful assistant.", temperature: float = 0.3) -> str:
        """
        Generate text using Kimi/Moonshot API (OpenAI compatible).
        """
        if not self.api_key:
            logger.error("Attempted to call Moonshot API without API Key.")
            return "{}" # Return empty JSON-like string to avoid hard crashes if parsed, or handle upstream
        
        url = f"{self.api_base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 2000 # Adjust as needed
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        logger.error(f"Moonshot API Error {response.status}: {error_text}")
                        raise Exception(f"AI API Failed: {response.status}")
                    
                    data = await response.json()
                    content = data['choices'][0]['message']['content']
                    return content
        except Exception as e:
            logger.error(f"Moonshot Client Exception: {e}")
            raise e

# Singleton
ai_client = MoonshotClient()
