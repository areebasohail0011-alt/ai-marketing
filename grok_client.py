"""
grok_client.py
Thin wrapper around the Groq chat completions API (api.groq.com).

Note: this uses Groq (the fast-inference company, api.groq.com), NOT xAI's
Grok (api.x.ai). Groq offers a free tier and hosts open models like Llama.

Security note: the API key is NEVER hard-coded. It is read from the
environment variable GROQ_API_KEY. Set it in Colab with:

    import os
    from getpass import getpass
    os.environ["GROQ_API_KEY"] = getpass("Enter your Groq API key: ")

or, on Streamlit Community Cloud, via st.secrets (see README).
"""

import os
import json
import re
import time
import requests

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
# openai/gpt-oss-20b is a smaller model with a higher free-tier token-per-minute
# (TPM) quota than the 120b version, which matters a lot for this multi-stage
# pipeline where each call carries growing context from earlier stages.
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")


class GrokAPIError(Exception):
    """Raised for any recoverable failure talking to the Groq API."""
    def __init__(self, code: str, detail: str = ""):
        self.code = code          # "MISSING_KEY" | "REQUEST_FAILED" | "MALFORMED_RESPONSE"
        self.detail = detail
        super().__init__(f"{code}: {detail}")


def _get_api_key() -> str:
    """
    Looks for the key in two places so the same code works both locally/Colab
    (environment variable) and on Streamlit Community Cloud (st.secrets,
    configured in the app's dashboard, never committed to GitHub).
    """
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        try:
            import streamlit as st
            api_key = st.secrets.get("GROQ_API_KEY")
        except Exception:
            api_key = None
    if not api_key:
        raise GrokAPIError("MISSING_KEY", "GROQ_API_KEY is not set (checked env var and st.secrets).")
    return api_key


def _extract_retry_seconds(error_body: str, default: float = 5.0) -> float:
    """Groq's 429 response includes 'Please try again in 14.16s' - parse that
    out so we wait exactly as long as needed instead of guessing."""
    match = re.search(r"try again in ([\d.]+)s", error_body)
    if match:
        return float(match.group(1)) + 1.0  # small safety buffer
    return default


def call_grok(system_prompt: str, user_prompt: str,
               temperature: float = 0.6, max_tokens: int = 900,
               _retries: int = 4) -> str:
    """Call the Groq chat completions endpoint. Returns raw text content.
    Automatically retries on rate-limit (429) or transient server errors
    (5xx). For 429s specifically, it parses Groq's exact 'try again in Xs'
    hint from the response body and waits that long, since free-tier TPM
    limits reset on a rolling per-minute window."""
    api_key = _get_api_key()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": temperature,
        "max_tokens": max_tokens,
    }

    last_error_detail = ""
    for attempt in range(_retries):
        try:
            resp = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=60)
            if resp.status_code == 429:
                last_error_detail = f"429: {resp.text}"
                wait = _extract_retry_seconds(resp.text)
                time.sleep(wait)
                continue
            if resp.status_code >= 500:
                last_error_detail = f"{resp.status_code}: {resp.text}"
                time.sleep(2 ** attempt * 2)
                continue
            resp.raise_for_status()
        except requests.exceptions.RequestException as e:
            detail = str(e)
            try:
                detail = f"{e} | body: {resp.text}"
            except Exception:
                pass
            raise GrokAPIError("REQUEST_FAILED", detail)

        try:
            data = resp.json()
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise GrokAPIError("MALFORMED_RESPONSE", str(e))

    raise GrokAPIError("REQUEST_FAILED", f"Rate limited after {_retries} retries. Last response: {last_error_detail}")


def _attempt_bracket_repair(text: str) -> str:
    """Scans the text tracking open/close brackets (ignoring bracket-like
    characters inside quoted strings) and appends whatever closing brackets
    are missing. Fixes the common case where the model's response was cut
    off by exactly the token limit, right at or near the very end - this
    happens often enough that it's worth trying before an expensive extra
    API call."""
    stack = []
    in_string = False
    escape = False
    for ch in text:
        if in_string:
            if escape:
                escape = False
            elif ch == '\\':
                escape = True
            elif ch == '"':
                in_string = False
        else:
            if ch == '"':
                in_string = True
            elif ch in '{[':
                stack.append(ch)
            elif ch in '}]':
                if stack:
                    stack.pop()
    repaired = text.rstrip()
    if repaired.endswith(","):
        repaired = repaired[:-1]
    if in_string:
        repaired += '"'
    for opener in reversed(stack):
        repaired += '}' if opener == '{' else ']'
    return repaired


def call_grok_json(system_prompt: str, user_prompt: str,
                    temperature: float = 0.4, max_tokens: int = 900) -> dict:
    """
    Calls Grok and attempts to parse the response as JSON.
    Strips markdown code fences if the model wraps its JSON in ```json ... ```.
    If parsing fails, tries three fallbacks in order, cheapest first:
      1. Auto-repair missing closing brackets (handles the common case of
         the response being cut off right at the token limit).
      2. Ask the model to fix its own broken JSON (handles structural
         issues like unrequested extra fields).
      3. Fall back to {"raw_text": "..."} so the UI never crashes.
    """
    raw = call_grok(system_prompt, user_prompt, temperature, max_tokens)
    cleaned = re.sub(r"^```(json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # Fallback 1: cheap, local bracket repair - no extra API call.
    try:
        return json.loads(_attempt_bracket_repair(cleaned))
    except json.JSONDecodeError:
        pass

    # Fallback 2: ask the model to fix its own broken JSON.
    try:
        repair_prompt = (
            "The text below was supposed to be strictly valid JSON but failed "
            "to parse (likely due to extra unrequested fields or a missing "
            "brace). Return ONLY the corrected, valid JSON with the same data "
            "and the same keys the original schema asked for - no extra keys, "
            "no commentary, no markdown code fences.\n\n"
            f"{cleaned[:4000]}"
        )
        raw2 = call_grok(
            "You are a JSON repair assistant. You output only valid, parseable JSON.",
            repair_prompt, temperature=0.0, max_tokens=max_tokens,
        )
        cleaned2 = re.sub(r"^```(json)?|```$", "", raw2.strip(), flags=re.MULTILINE).strip()
        return json.loads(cleaned2)
    except Exception:
        return {"raw_text": raw}
