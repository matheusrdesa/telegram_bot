import os
from fastapi import FastAPI, Request, Header, HTTPException
import httpx
from collections import defaultdict, deque
from typing import Deque, Dict, Optional
from openai import OpenAI

# === Config via variáveis de ambiente ===
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
MODEL_ID = os.environ.get("MODEL_ID", "llama-3.1-8b-instant")  # modelo default do Groq
WEBHOOK_SECRET = os.environ.get("WEBHOOK_SECRET", "")  # opcional, recomendado

if not TELEGRAM_TOKEN:
    raise RuntimeError("Faltou TELEGRAM_TOKEN no ambiente.")
if not GROQ_API_KEY:
    raise RuntimeError("Faltou GROQ_API_KEY no ambiente.")

# Endpoints
BOT_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"

# Cliente OpenAI apontando para o endpoint compatível do Groq
client = OpenAI(base_url="https://api.groq.com/openai/v1", api_key=GROQ_API_KEY)

app = FastAPI(title="Telegram LLM Bot (Groq)")

# histórico simples em memória (últimas 10 trocas por chat)
History = Dict[int, Deque[dict]]
history: History = defaultdict(lambda: deque(maxlen=10))

async def send_message(chat_id: int, text: str):
    async with httpx.AsyncClient(timeout=20) as http:
        await http.post(f"{BOT_API}/sendMessage", json={"chat_id": chat_id, "text": text})

@app.get("/")
def health():
    return {"status": "ok"}

@app.post("/webhook/{token}")
async def handle_update(
    token: str,
    request: Request,
    x_telegram_bot_api_secret_token: Optional[str] = Header(default=None),
):
    # 1) segurança do path: usamos o próprio TOKEN na URL do webhook
    if token != TELEGRAM_TOKEN:
        raise HTTPException(403, "invalid path token")
    # 2) segurança do header: se definimos WEBHOOK_SECRET, validamos o header
    if WEBHOOK_SECRET and x_telegram_bot_api_secret_token != WEBHOOK_SECRET:
        raise HTTPException(403, "invalid secret token")

    update = await request.json()
    message = update.get("message") or update.get("edited_message")
    if not message or "text" not in message:
        return {"ok": True}

    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    # comandos simples
    if text.startswith("/start"):
        await send_message(chat_id, "Olá! Sou um bot com Llama 3.1 (Groq). Mande sua pergunta. 🤖")
        return {"ok": True}
    if text.startswith("/help"):
        await send_message(chat_id, "Envie uma pergunta em português. Use /reset para limpar o histórico.")
        return {"ok": True}
    if text.startswith("/reset"):
        history[chat_id].clear()
        await send_message(chat_id, "Histórico limpo. Pode continuar!")
        return {"ok": True}

    # monta contexto
    msgs = list(history[chat_id])
    msgs.append({"role": "user", "content": text})

    # chamada ao LLM (Groq, via API OpenAI-compatível)
    completion = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": "Responda em português do Brasil, de forma objetiva e útil."}
        ] + msgs,
        temperature=0.7,
        max_tokens=512,
    )
    answer = completion.choices[0].message.content

    # persiste histórico em memória
    history[chat_id].append({"role": "user", "content": text})
    history[chat_id].append({"role": "assistant", "content": answer})

    await send_message(chat_id, answer)
    return {"ok": True}
