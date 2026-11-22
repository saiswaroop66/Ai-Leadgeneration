
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
DEFAULT_MODEL = "llama3.2"


def generate_email_reply(email, extra_instruction="", model=DEFAULT_MODEL):

    sender = email.get("from", "Unknown sender")
    subject = email.get("subject", "(No subject)")
    body = (email.get("body") or "").strip()

    if not body:
        raise ValueError(
            "The email body is empty. Cannot generate a reply."
        )

    prompt = f"""
You are a professional business email assistant.

Write a concise, polite and natural reply to this email.

Rules:
- Reply directly to what the sender said.
- Do not invent prices, promises or dates.
- Do not make false claims.
- Ask questions if information is missing.
- Use a professional greeting and sign-off.
- Return only the email reply.

Sender: {sender}
Subject: {subject}

Incoming email:
{body}

Additional instructions:
{extra_instruction.strip() or "No additional instructions."}

Write the reply now:
"""

    try:
        response = requests.post(
            OLLAMA_URL,
            json={
                "model": model,
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

    result = response.json().get("response", "").strip()

    if not result:
        raise RuntimeError("Ollama returned an empty response.")

    return result
