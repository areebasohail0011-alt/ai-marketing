"""
prompts.py
All prompt templates for the 8-stage pipeline described in the PRD:
1. Business Understanding
2. Target Customer Analysis (folded into stage 1's output)
3. Competitor Discovery
4. Competitor Comparison
5. Opportunity / Gap Detection
6. Positioning
7. Marketing Strategy (+ content ideas + campaign)
8. Action Plan

Every stage:
- gets the original business_info dict
- gets the accumulated "context" (outputs of earlier stages) so later
  stages are grounded in earlier ones, per the PRD's pipeline requirement
- is instructed to output STRICT JSON so the Streamlit UI can render it
  in structured sections instead of raw text
- is instructed to clearly flag anything that is an AI estimate rather
  than verified data (PRD sections 8, 11, 26)
"""

BASE_SYSTEM_PROMPT = (
    "You are AI Marketing Co-Pilot, an AI marketing strategist for startups and "
    "small businesses. You give specific, practical, business-tailored advice, "
    "never generic filler. You always output valid JSON only, matching the exact "
    "schema requested, with no markdown, no commentary, and no code fences. "
    "You never present invented statistics, market sizes, or competitor data as "
    "verified fact. If information is not knowable, mark it clearly as an AI "
    "estimate or leave it out."
)


def _trim(context_value, max_chars: int = 900) -> str:
    """Stringifies and trims a prior stage's output before embedding it in the
    next prompt. Keeps token usage bounded even as the pipeline accumulates
    more context stage by stage - important for Groq's free-tier TPM limits."""
    text = str(context_value)
    if len(text) > max_chars:
        return text[:max_chars] + "...(truncated)"
    return text


def _business_block(business: dict) -> str:
    return f"""
BUSINESS INFORMATION
Business Name: {business.get('name')}
Product/Service: {business.get('product')}
Description: {business.get('description')}
Location/Target Country: {business.get('location')}
Target Audience: {business.get('audience')}
Marketing Budget: {business.get('budget')}
Business Stage: {business.get('stage')}
Known Competitors (may be empty): {business.get('known_competitors') or 'None provided'}
"""


def stage1_business_analysis(business: dict) -> str:
    return _business_block(business) + """
TASK: Analyze this business. Output JSON with EXACTLY these keys:
{
  "business_type": string,
  "product_category": string,
  "target_customer": string,
  "customer_needs": [string, ...],
  "value_proposition": string,
  "marketing_challenges": [string, ...],
  "positioning_opportunity": string
}
"""


def stage2_competitor_discovery(business: dict, context: dict) -> str:
    known = business.get("known_competitors")
    mode = "The user provided known competitors below; validate and enrich them." \
        if known else \
        "The user does NOT know their competitors. Generate a plausible discovery list " \
        "of competitor names or competitor categories based on the business profile."
    return _business_block(business) + f"""
BUSINESS ANALYSIS SO FAR: {_trim(context.get('stage1'))}

TASK: {mode}
This is AI-generated market intelligence, NOT guaranteed real-time data - say so.
Output JSON with EXACTLY these keys:
{{
  "disclaimer": "short one-line note that this is AI-generated intelligence, not verified real-time data",
  "competitors": [
    {{"name": string, "category": string, "why_relevant": string}}
  ]
}}
Return 3-5 competitors.
"""


def stage3_competitor_analysis(business: dict, context: dict) -> str:
    return _business_block(business) + f"""
COMPETITORS TO ANALYZE: {_trim(context.get('stage2'))}
BUSINESS ANALYSIS: {_trim(context.get('stage1'))}

TASK: For each competitor, produce a structured marketing analysis, and then state
the opportunity for OUR business relative to that competitor.
Output JSON with EXACTLY these keys:
{{
  "competitor_table": [
    {{
      "name": string,
      "target_audience": string,
      "price_positioning": string,
      "brand_positioning": string,
      "main_channels": [string, ...],
      "content_approach": string,
      "strengths": [string, ...],
      "weaknesses": [string, ...],
      "usp": string,
      "threat_level": "Low" | "Medium" | "High",
      "our_opportunity": string
    }}
  ]
}}
"""


def stage4_market_gap(business: dict, context: dict) -> str:
    return _business_block(business) + f"""
COMPETITOR ANALYSIS: {_trim(context.get('stage3'))}
BUSINESS ANALYSIS: {_trim(context.get('stage1'))}

TASK: Identify 1-3 underserved segments or market gaps this business could exploit.
For each gap explain: what it is, why it's an opportunity, which segment it applies to,
and how the business could respond.
Output JSON with EXACTLY these keys:
{{
  "gaps": [
    {{
      "gap": string,
      "why_opportunity": string,
      "target_segment": string,
      "recommended_response": string
    }}
  ]
}}
"""


def stage5_positioning(business: dict, context: dict) -> str:
    return _business_block(business) + f"""
MARKET GAPS: {_trim(context.get('stage4'))}
COMPETITOR ANALYSIS: {_trim(context.get('stage3'))}
BUSINESS ANALYSIS: {_trim(context.get('stage1'))}

TASK: Recommend a positioning strategy grounded in the above.
Output JSON with EXACTLY these keys:
{{
  "recommended_target_customer": string,
  "brand_positioning": string,
  "value_proposition": string,
  "usp": string,
  "key_differentiator": string,
  "suggested_brand_message": string
}}
"""


def stage6_marketing_strategy(business: dict, context: dict) -> str:
    return _business_block(business) + f"""
POSITIONING: {_trim(context.get('stage5'))}
MARKET GAPS: {_trim(context.get('stage4'))}

TASK: Recommend a marketing strategy tailored to the audience, budget and stage.
Only recommend channels that make sense for this business - do not list every channel
(at most 5 channels). Also propose ONE concrete campaign concept with a short
day-by-day content outline (at most 7 steps, one short sentence each).
IMPORTANT: Output ONLY the exact keys listed below. Do NOT add any extra keys
(such as "budget") anywhere in the JSON, even inside nested objects - extra
keys break parsing. Output strictly valid JSON, nothing before or after it.
{{
  "recommended_channels": [{{"channel": string, "why": string}}],
  "content_types": [string, ...],
  "campaign": {{
    "name": string,
    "goal": string,
    "outline": [{{"day_or_step": string, "content": string}}]
  }}
}}
"""


def stage7_action_plan(business: dict, context: dict) -> str:
    return _business_block(business) + f"""
MARKETING STRATEGY: {_trim(context.get('stage6'))}
POSITIONING: {_trim(context.get('stage5'))}

TASK: Create a practical 30-day marketing action plan broken into 4 weeks,
appropriate for the stated budget and business stage.
IMPORTANT LENGTH RULE: List AT MOST 5 tasks per week, and keep each task to
one short sentence. This keeps the plan focused and ensures the JSON output
is never cut off.
IMPORTANT: Output ONLY the exact keys listed below. Do NOT add any extra keys
(such as "budget") anywhere in the JSON, even inside individual week objects -
extra keys break parsing. Every week must be its own complete {{"week": ..., "tasks": [...]}}
object inside the "weeks" array. Output strictly valid JSON, nothing before or after it.
{{
  "weeks": [
    {{"week": "Week 1 - Foundation", "tasks": [string, ...]}},
    {{"week": "Week 2 - Content", "tasks": [string, ...]}},
    {{"week": "Week 3 - Audience Growth", "tasks": [string, ...]}},
    {{"week": "Week 4 - Campaign", "tasks": [string, ...]}}
  ]
}}
"""


def assistant_system_prompt(business: dict, context: dict) -> str:
    return (
        BASE_SYSTEM_PROMPT.replace("You always output valid JSON only, matching the exact "
                                   "schema requested, with no markdown, no commentary, and no code fences. ", "")
        + "\nYou are now in free-form Q&A mode. Answer conversationally and practically. "
        + f"\n\nFull business context so far:\n{_business_block(business)}\n"
        + f"Prior analysis:\n{context}\n"
    )
