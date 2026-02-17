"""Kimi K2.5 (Moonshot AI) Analyzer for LinkedIn Screenshots"""
import logging
import json
import time
from typing import List, Dict, Any, Optional
from openai import OpenAI
from pydantic import BaseModel, Field

from src.core.config import settings
from src.core.data_types import AIAnalysisOutput

logger = logging.getLogger(__name__)

# Pydantic models for validation
class ExtractedAnnouncement(BaseModel):
    company_name: str
    vc_firm: str
    round_type: Optional[str] = None
    amount_raised_gbp: Optional[int] = None
    description: Optional[str] = None
    sector: Optional[str] = None

class AnalysisResult(BaseModel):
    announcements: List[ExtractedAnnouncement]

class KimiAnalyzer:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.moonshot_api_key,
            base_url=settings.kimi_api_base
        )
        self.model = settings.kimi_model
        self.token_cost_per_million = 0.07  # Placeholder approximation

    async def analyze_screenshots(self, screenshots: List[str]) -> AIAnalysisOutput:
        """Batch analyze screenshots to extract VC announcements"""
        if not screenshots:
            return AIAnalysisOutput(
                input_id="empty",
                analysis_type="linkedin_feed_analysis",
                result={"announcements": []},
                confidence=1.0,
                reasoning="No screenshots provided"
            )

        logger.info(f"Analyzing {len(screenshots)} screenshots with Kimi...")
        
        # Prepare messages
        messages = self._build_prompt(screenshots)
        
        start_time = time.time()
        retries = 3
        
        for attempt in range(retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    response_format={"type": "json_object"},
                    max_tokens=4000
                )
                
                content = response.choices[0].message.content
                tokens = response.usage.total_tokens
                cost = (tokens / 1_000_000) * self.token_cost_per_million
                
                logger.info(f"Analysis complete. Tokens: {tokens}, Cost: ${cost:.6f}")
                
                parsed_result = self._parse_response(content)
                
                return AIAnalysisOutput(
                    input_id=f"batch_{int(start_time)}",
                    analysis_type="linkedin_feed_analysis",
                    result=parsed_result,
                    confidence=1.0,  # Trusting the model for now
                    reasoning="Extracted from screenshots",
                    tokens_used=tokens,
                    cost_usd=cost
                )
                
            except Exception as e:
                logger.error(f"Error calling Kimi API (attempt {attempt+1}/{retries}): {e}")
                if attempt == retries - 1:
                    raise
                time.sleep(2 ** attempt)  # Exponential backoff

        raise RuntimeError("Failed to analyze screenshots after retries")

    def _build_prompt(self, screenshots: List[str]) -> List[Dict[str, Any]]:
        """Construct prompt with images"""
        content = [
            {
                "type": "text", 
                "text": (
                    "Analyze these LinkedIn posts. Extract any NEW Venture Capital investment or funding announcements. "
                    "Ignore generic news, ads, or old posts. "
                    "Focus on identifying: Company Name, VC Firm(s), Round Type (Seed, Series A, etc.), "
                    "Amount Raised (Convert to GBP if in USD/EUR, use 0.8 rate for USD, 0.85 for EUR), "
                    "Description of the company/round, and Sector. "
                    "Return ONLY valid JSON with this structure: "
                    "{'announcements': [{'company_name': '...', 'vc_firm': '...', 'round_type': '...', "
                    "'amount_raised_gbp': 123456, 'description': '...', 'sector': '...'}]}"
                )
            }
        ]
        
        # Add images
        # Note: Kimi/Moonshot supports images in user messages
        # Depending on Kimi's exact API for multiple images, we iterate.
        # Assuming standard OpenAI vision compatibility:
        for b64_img in screenshots:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/jpeg;base64,{b64_img}"
                }
            })
            
        return [
            {"role": "system", "content": "You are a specialized VC investment analyst AI."},
            {"role": "user", "content": content}
        ]

    def _parse_response(self, response_content: str) -> Dict[str, Any]:
        """Parse and validate JSON response"""
        try:
            data = json.loads(response_content)
            # Basic validation
            validated = AnalysisResult(**data)
            return validated.model_dump()
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.debug(f"Raw content: {response_content}")
            return {"announcements": []}
        except Exception as e:
            logger.error(f"Validation error: {e}")
            return {"announcements": []}
