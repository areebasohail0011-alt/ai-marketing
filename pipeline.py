"""
pipeline.py
Runs the staged AI pipeline described in PRD section 22:
Business Understanding -> Competitor Discovery -> Competitor Comparison
-> Gap Detection -> Positioning -> Marketing Strategy -> Action Plan

Each stage feeds its output into the next stage's context, so the model
stays grounded in everything decided before it (this is what makes the
tool "connect" insights rather than generate 8 disconnected answers).

A small delay is added between stages to stay well under Groq's free-tier
per-minute rate limits, since 7 back-to-back calls can otherwise trigger
429 responses.
"""

import time
from grok_client import call_grok_json, GrokAPIError
import prompts

STAGES = [
    ("stage1", "Analyzing your business & target audience", prompts.stage1_business_analysis, False, 700),
    ("stage2", "Discovering competitors", prompts.stage2_competitor_discovery, True, 900),
    ("stage3", "Analyzing competitors", prompts.stage3_competitor_analysis, True, 1500),
    ("stage4", "Detecting market gaps", prompts.stage4_market_gap, True, 900),
    ("stage5", "Recommending positioning", prompts.stage5_positioning, True, 700),
    ("stage6", "Building marketing strategy", prompts.stage6_marketing_strategy, True, 1300),
    ("stage7", "Creating your 30-day action plan", prompts.stage7_action_plan, True, 1800),
]

DELAY_BETWEEN_STAGES_SECONDS = 4


def run_pipeline(business: dict, progress_callback=None) -> dict:
    """
    Runs all stages sequentially. progress_callback(label, step, total) is
    called before each stage if provided (used to drive a Streamlit progress bar).
    Returns the accumulated context dict, e.g. {"stage1": {...}, "stage2": {...}, ...}
    Raises GrokAPIError if any stage fails (caller should catch and show a
    friendly message + retry option, per PRD section 24).
    """
    context = {}
    total = len(STAGES)

    for i, (key, label, builder, needs_context, stage_max_tokens) in enumerate(STAGES, start=1):
        if progress_callback:
            progress_callback(label, i, total)

        user_prompt = builder(business, context) if needs_context else builder(business)
        result = call_grok_json(prompts.BASE_SYSTEM_PROMPT, user_prompt, max_tokens=stage_max_tokens)
        context[key] = result

        if i < total:
            time.sleep(DELAY_BETWEEN_STAGES_SECONDS)

    return context
