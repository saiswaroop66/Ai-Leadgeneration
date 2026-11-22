
from modules.ollama_ai import OLLAMA_URL, DEFAULT_MODEL
import requests


def generate_followup_email(lead, followup_number=1, extra_instruction=""):

    business_name = lead.get(
        "business_name", "Business"
    )

    email = lead.get("email", "")

    category = lead.get(
        "category", "business"
    )

    city = lead.get(
        "city", ""
    )

    history = lead.get(
        "outreach_history", []
    )

    previous_followups = sum(
        1 for item in history
        if str(item.get("stage", "")).startswith("followup_")
    )

    if followup_number not in [1, 2]:
        raise ValueError("Only first and second follow-ups are supported.")

    if not email:
        raise ValueError("Business email address is missing.")

    if followup_number == 1:
        followup_context = "This is the first polite follow-up after the initial email."
    else:
        followup_context = "This is the second and final follow-up. Keep it polite, brief, and respectful."

    prompt = f"""
You are a professional business email writer.

Write a personalized follow-up email for this business.

Business name: {business_name}
Business category: {category}
City: {city}
Business email: {email}

Follow-up number: {followup_number}

Context:
{followup_context}

Rules:
- Sound professional, natural, and respectful.
- Mention the previous email without sounding demanding.
- Do not pretend the business has replied.
- Do not invent offers, prices, services, or promises.
- Keep the email concise.
- Include a suitable subject line.
- Return exactly this format:

SUBJECT: Your subject

BODY:
Your email message

Additional instructions:
{extra_instruction.strip() or "No additional instructions."}
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": DEFAULT_MODEL,
                "prompt": prompt,
                "stream": False
            },
            timeout=180
        )

        response.raise_for_status()

    except requests.exceptions.ConnectionError as error:
        raise RuntimeError(
            "Cannot connect to Ollama. Make sure Ollama is running."
        ) from error

    except requests.exceptions.Timeout as error:
        raise RuntimeError(
            "Ollama took too long. Please try again."
        ) from error

    except requests.exceptions.HTTPError as error:
        raise RuntimeError(
            f"Ollama error: {response.text[:500]}"
        ) from error

    result = response.json().get(
        "response", ""
    ).strip()

    if not result:
        raise RuntimeError(
            "Ollama returned an empty response."
        )

    if "BODY:" not in result:
        raise RuntimeError(
            "AI did not return the expected subject and body format. Please regenerate."
        )

    return result
