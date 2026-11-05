import base64
import json
import mimetypes
import time
import urllib.error
import urllib.request
from pathlib import Path

from ..config import Config


class GeminiUnavailable(RuntimeError):
    pass


def _parse_json_response(text: str) -> dict:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned
        cleaned = cleaned.rsplit("```", 1)[0].strip()
    try:
        value = json.loads(cleaned)
    except json.JSONDecodeError:
        start, end = cleaned.find("{"), cleaned.rfind("}")
        if start < 0 or end <= start:
            raise
        value = json.loads(cleaned[start:end + 1])
    if not isinstance(value, dict):
        raise json.JSONDecodeError("Gemini response was not a JSON object", cleaned, 0)
    return value


def _available_models() -> list[str]:
    endpoint = f"https://generativelanguage.googleapis.com/v1beta/models?key={Config.GEMINI_API_KEY}"
    request = urllib.request.Request(endpoint, headers={"Accept": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            models = json.loads(response.read().decode("utf-8")).get("models", [])
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return []
    return [
        model["name"].removeprefix("models/")
        for model in models
        if "generateContent" in model.get("supportedGenerationMethods", [])
        and "flash" in model.get("name", "").lower()
    ]


def review_image(path: Path, local_result: dict) -> dict:
    if not Config.GEMINI_API_KEY:
        raise GeminiUnavailable("GEMINI_API_KEY is not configured. Add it to .env; never put the key in frontend code.")
    mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    prompt = ("You are a research assistant, not a doctor. Review this retinal fundus image only as a second opinion. "
              "Do not claim diagnosis or certainty. Return JSON with keys image_quality, possible_observations, "
              "review_recommendation, and disclaimer. Do not produce a replacement class label. "
              f"The local model output is for comparison only: {json.dumps(local_result)}")
    payload = {"contents": [{"parts": [{"text": prompt}, {"inline_data": {"mime_type": mime_type, "data": encoded}}]}], "generationConfig": {"temperature": 0.0, "responseMimeType": "application/json"}}
    models = [Config.GEMINI_MODEL]
    for available in _available_models():
        if available not in models:
            models.append(available)
    body = None
    last_error = None
    for model_name in models:
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={Config.GEMINI_API_KEY}"
        request = urllib.request.Request(endpoint, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        for attempt in range(3):
            try:
                with urllib.request.urlopen(request, timeout=60) as response:
                    body = json.loads(response.read().decode("utf-8"))
                break
            except urllib.error.HTTPError as exc:
                details = exc.read().decode("utf-8", errors="replace")
                last_error = f"HTTP {exc.code}: {details[:500]}"
                if exc.code == 503 and attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                if exc.code == 404:
                    break
                break
            except (urllib.error.URLError, TimeoutError) as exc:
                last_error = str(exc)
                if attempt < 2:
                    time.sleep(2 ** attempt)
                    continue
                break
        if body is not None:
            break
    if body is None:
        if last_error and "HTTP 503" in last_error:
            raise GeminiUnavailable("Gemini is temporarily busy or rate-limited. Wait a minute and try again, or use the local prediction.")
        raise GeminiUnavailable(f"Gemini request failed: {last_error or 'no response'}")
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
        review = _parse_json_response(text)
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as exc:
        raise GeminiUnavailable("Gemini returned an unreadable response") from exc
    observations = review.get("possible_observations", [])
    if isinstance(observations, str):
        observations = [observations]
    elif not isinstance(observations, list):
        observations = [str(observations)]
    review["possible_observations"] = observations
    review["provider"] = "Google Gemini research second opinion"
    review["local_model_result"] = local_result
    return review