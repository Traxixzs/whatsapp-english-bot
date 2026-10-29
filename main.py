import os
import requests
from fastapi import FastAPI, Request, Response, Query
from groq import Groq

app = FastAPI()

# Récupération des variables d'environnement
GROQ_API_KEY = os.environ.get("GROQ_API_KEY")
WHATSAPP_TOKEN = os.environ.get("WHATSAPP_TOKEN")
PHONE_NUMBER_ID = os.environ.get("PHONE_NUMBER_ID")
VERIFY_TOKEN = os.environ.get("VERIFY_TOKEN", "mon_token_secret_123")

groq_client = Groq(api_key=GROQ_API_KEY)

SYSTEM_PROMPT = """You are an adaptive English conversation tutor on WhatsApp.
Your goal is to help the user practice English naturally.

Guidelines:
1. Target level: Adapt your vocabulary and grammar to be slightly above the user's detected level (i+1 learning principle).
2. Format: Keep responses concise (1 to 3 sentences maximum) for a natural chat pace.
3. Flow: Always end your response with an open-ended question to keep the conversation going.
4. Corrections: If the user makes a clear grammar or spelling error, append a polite correction at the end using this exact format:
   💡 *Tip:* [short correction and brief explanation]
5. Language: Always reply in English. If the user writes in French, reply in simplified English with a quick French translation in parentheses."""

# Validation du Webhook par Meta
@app.get("/webhook")
async def verify_webhook(
    mode: str = Query(None, alias="hub.mode"),
    token: str = Query(None, alias="hub.verify_token"),
    challenge: str = Query(None, alias="hub.challenge")
):
    if mode == "subscribe" and token == VERIFY_TOKEN:
        return Response(content=challenge, status_code=200)
    return Response(content="Verification failed", status_code=403)

# Réception et traitement des messages WhatsApp
@app.post("/webhook")
async def receive_whatsapp(request: Request):
    data = await request.json()
    
    try:
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])
        
        if messages:
            msg = messages[0]
            if msg.get("type") == "text":
                user_text = msg["text"]["body"]
                from_number = msg["from"]
                
                # 1. Génération de la réponse adaptative via Groq
                completion = groq_client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": SYSTEM_PROMPT},
                        {"role": "user", "content": user_text}
                    ],
                    temperature=0.7,
                    max_tokens=200
                )
                ai_reply = completion.choices[0].message.content
                
                # 2. Envoi du message retour sur WhatsApp
                send_whatsapp_message(from_number, ai_reply)
    except Exception as e:
        print(f"Error processing webhook: {e}")
        
    return {"status": "success"}

def send_whatsapp_message(to_number: str, text: str):
    url = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": text}
    }
    requests.post(url, json=payload, headers=headers)
