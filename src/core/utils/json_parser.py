import json
import re
from typing import Dict, Any, Optional

def extract_json_from_text(text: str) -> Optional[Dict[str, Any]]:
    """
    Tries to extract the first valid JSON block from a text string.
    Handles markdown (```json ... ```) and other surrounding text.
    """
    if not text:
        return None

    # Try to find a JSON code block
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        json_str = match.group(1)
    else:
        # If no markdown, search for the first "loose" JSON object
        match = re.search(r'(\{.*?\})', text, re.DOTALL)
        if not match:
            return None
        json_str = match.group(0)

    try:
        return json.loads(json_str)
    except json.JSONDecodeError:
        # Try to fix common errors, like trailing commas
        try:
            corrected_str = re.sub(r',\s*([\}\]])', r'\1', json_str)
            return json.loads(corrected_str)
        except json.JSONDecodeError:
            return None
