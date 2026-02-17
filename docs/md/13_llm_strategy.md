# LLM Strategy & Model Selection

RADAR uses Large Language Models for advanced analysis tasks. This document explains which models are used, where, and how to configure them.

## Primary Stack

### 1. Kimi (Moonshot AI) - Primary Production Model
**Model**: `moonshot-v1-128k`  
**Provider**: Moonshot AI (https://platform.moonshot.cn)  
**API Key**: `MOONSHOT_API_KEY` in `.env`

**Used For**:
- **Moat Analysis** (`src.universe.llm_moat_analyzer`): Evaluating the 5-Pillar Investment Thesis
- **Competitive Intelligence** (`src.competitive.kimi_analyzer`): Parsing LinkedIn screenshots to extract VC announcements
- **Vision Tasks**: Screenshot analysis for visual scraping workflows

**Why Kimi?**:
- Strong performance on business/financial analysis tasks
- Vision capabilities (multimodal) for screenshot parsing
- Cost-effective for high-volume usage
- 128K context window for processing long documents

### 2. OpenAI - Development & Fallback
**Models**: `gpt-4o`, `gpt-4o-mini`  
**Provider**: OpenAI  
**API Key**: `OPENAI_API_KEY` in `.env`

**Used For**:
- Development testing and prototyping
- Fallback when Kimi API is unavailable
- Experimental features requiring cutting-edge capabilities

## Configuration

### Setting the Active Model
The `src.core.ai_client` module abstracts LLM calls. To switch providers:

1. **For Moat Analysis**: Edit `src.universe.llm_moat_analyzer.py`
   ```python
   # Line ~10
   MODEL = "moonshot-v1-128k"  # Change to "gpt-4o" for OpenAI
   ```

2. **For Competitive Radar**: Edit `src.competitive.kimi_analyzer.py`
   ```python
   # Line ~15
   model="moonshot-v1-128k"  # Change as needed
   ```

### Environment Variables
```bash
# .env file
MOONSHOT_API_KEY=your_moonshot_key_here
OPENAI_API_KEY=your_openai_key_here  # Optional
```

## Prompt Strategies

### Moat Analysis Prompt
Located in `src.universe.llm_moat_analyzer.py`, the prompt:
- Provides the 5-Pillar framework definition
- Includes examples of strong vs. weak moats
- Requires JSON output with evidence and scores (0-100 per pillar)

### Competitive Analysis Prompt
Located in `src.competitive.kimi_analyzer.py`, the prompt:
- Analyzes LinkedIn post screenshots
- Extracts: Company Name, VC Firm, Round Size, Sector
- Returns structured JSON array

## Cost Management

**Typical Usage**:
- Moat Analysis: ~2,000 tokens/company (input + output)
- Competitive Scan: ~5,000 tokens/screenshot

**Recommendations**:
- Use Kimi for production (lower cost)
- Batch requests where possible
- Cache LLM results in `company.moat_analysis` JSON field to avoid repeat calls

## Future Models

The system is designed to be model-agnostic. To add a new provider:
1. Update `src.core.ai_client` with the new API integration
2. Update module-specific analyzers to reference the new model name
3. Document the change in this file
