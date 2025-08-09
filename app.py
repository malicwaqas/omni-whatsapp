import os, json, datetime, httpx
from fastapi import FastAPI, Request, Response
from openai import OpenAI

app = FastAPI()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
GRAPH = "https://graph.facebook.com/v20.0"
PHONE_ID = os.getenv("WHATSAPP_PHONE_ID")
TOKEN = os.getenv("WHATSAPP_TOKEN")
VERIFY = os.getenv("WHATSAPP_VERIFY_TOKEN")
CITY = os.getenv("HOME_CITY", "Dubai,AE")

async def wa_send_text(to, text):
    async with httpx.AsyncClient(timeout=20) as s:
        await s.post(f"{GRAPH}/{PHONE_ID}/messages",
            headers={"Authorization": f"Bearer {TOKEN}"},
            json={
                "messaging_product": "whatsapp",
                "to": to,
                "type": "text",
                "text": {"body": text[:4096]}
            })

@app.get("/health")
async def health():
    return {"ok": True}

@app.get("/whatsapp/webhook")
async def verify(mode: str = None, challenge: str = None, token: str = None):
    if mode == "subscribe" and token == VERIFY:
        return Response(content=challenge or "", media_type="text/plain")
    return Response(status_code=403)

@app.post("/whatsapp/webhook")
async def webhook(req: Request):
    body = await req.json()
    for entry in body.get("entry", []):
        val = entry.get("changes", [{}])[0].get("value", {})
        for msg in val.get("messages", []):
            if msg.get("type") != "text":
                continue
            frm = msg["from"]
            text = msg["text"]["body"].strip()

            if text.lower() in ("hi", "hello", "/start", "start"):
                await wa_send_text(frm, "Hey! I’m OmniAI. Try: `brief`, `summarize <url>`.")
                continue

            if text.lower
