import os, datetime, httpx
from fastapi import FastAPI, Request, Response
from openai import OpenAI

app = FastAPI()

# --- Config ---
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID", "")
TOKEN = os.getenv("WHATSAPP_TOKEN", "")
VERIFY = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
CITY = os.getenv("HOME_CITY", "Dubai")
GRAPH = "https://graph.facebook.com/v20.0"

client = OpenAI(api_key=OPENAI_API_KEY)

# --- WhatsApp send helper ---
async def wa_send_text(to: str, text: str):
    if not (PHONE_ID and TOKEN):
        return
    async with httpx.AsyncClient(timeout=20) as s:
        await s.post(
            f"{GRAPH}/{PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text[:4096]},
            },
        )

@app.get("/health")
async def health():
    return {"ok": True}

# --- Webhook verify (GET) ---
@app.get("/whatsapp/webhook")
async def verify(mode: str | None = None, challenge: str | None = None, token: str | None = None):
    if mode == "subscribe" and token == VERIFY:
        return Response(content=challenge or "", media_type="text/plain")
    return Response(status_code=403)

# --- Webhook receive (POST) ---
@app.post("/whatsapp/webhook")
async def webhook(req: Request):
    body = await req.json()
    for entry in body.get("entry", []):
        change = entry.get("changes", [{}])[0].get("value", {})
        for msg in change.get("messages", []):
            if msg.get("type") != "text":
                continue
            frm = msg["from"]
            text_raw = (msg.get("text", {}).get("body") or "").strip()
            text = text_raw.lower()

            # greetings
            if text in ("hi", "hello", "/start", "start"):
                await wa_send_text(frm, "Hey! I’m OmniAI. Try: `brief`, or `summarize <url>`.")
                continue

            # daily brief
            if text == "brief":
                async with httpx.AsyncClient(timeout=20) as s:
                    w = (await s.get(f"https://wttr.in/{CITY}?format=3")).text
                prompt = f"Make a crisp morning brief for {CITY} on {datetime.date.today()} including: {w}. Under 120 words."
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": prompt}],
                )
                await wa_send_text(frm, res.choices[0].message.content)
                continue

            # summarize a link
            if text.startswith("summarize "):
                url = text_raw.split(" ", 1)[1].strip()
                async with httpx.AsyncClient(timeout=20) as s:
                    html = (await s.get(url)).text[:20000]
                res = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[{"role": "user", "content": f"Summarize in 5 bullets:\n{html}"}],
                )
                await wa_send_text(frm, res.choices[0].message.content)
                continue

            # default chat
            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Helpful, concise assistant."},
                    {"role": "user", "content": text_raw},
                ],
            )
            await wa_send_text(frm, res.choices[0].message.content)
    return {"ok": True}
