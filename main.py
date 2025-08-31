import os
from fastapi import FastAPI, Request, Header, HTTPException
import httpx
from collections import defaultdict, deque
from typing import Deque, Dict, Optional
from openai import OpenAI
from typing import Tuple

# === Helper
async def send_typing(chat_id: int):
    async with httpx.AsyncClient(timeout=10) as http:
        await http.post(f"{BOT_API}/sendChatAction", json={"chat_id": chat_id, "action": "typing"})

def llm_params_for_mode(mode: str) -> Tuple[float, int]:
    if mode == "criativo":
        return 0.9, 768   # temperatura, max_tokens
    # default: curto
    return 0.5, 384

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
# preferências por chat (modo de resposta)
# modos: "curto" (rápido/barato) | "criativo" (mais detalhado)
chat_prefs: Dict[int, str] = defaultdict(lambda: "curto")

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
        await send_message(chat_id,
            "Olá! Sou um bot com Llama 3.1 (Groq). Use /help para ver os comandos. 🤖")
        return {"ok": True}

    if text.startswith("/help"):
        await send_message(chat_id,
            "Comandos:\n"
            "/help – ajuda rápida\n"
            "/about – sobre o bot\n"
            "/reset – limpa o histórico deste chat\n"
            "/mode – mostra ou define o modo (curto/criativo). Ex.: /mode criativo")
        return {"ok": True}

    if text.startswith("/about"):
        await send_message(chat_id,
            "Sou um bot em FastAPI usando modelos Llama 3.x na Groq (API compatível com OpenAI).")
        return {"ok": True}

    if text.startswith("/reset"):
        history[chat_id].clear()
        await send_message(chat_id, "Histórico limpo. Pode continuar!")
        return {"ok": True}

    if text.startswith("/mode"):
        parts = text.split()
        if len(parts) == 1:
            await send_message(chat_id, f"Modo atual: {chat_prefs[chat_id]} (opções: curto, criativo)")
        else:
            candidate = parts[1].strip().lower()
            if candidate in ("curto", "criativo"):
                chat_prefs[chat_id] = candidate
                await send_message(chat_id, f"Modo alterado para: {candidate}")
            else:
                await send_message(chat_id, "Modo inválido. Use: curto ou criativo.")
        return {"ok": True}

    # monta contexto
    await send_typing(chat_id)
    msgs = list(history[chat_id])
    msgs.append({"role": "user", "content": text})

    # chamada ao LLM (Groq, via API OpenAI-compatível)
    temperature, max_tokens = llm_params_for_mode(chat_prefs[chat_id])

    try:
        completion = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "Responda em português do Brasil, de forma objetiva e útil."}
            ] + msgs,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        answer = completion.choices[0].message.content or "Desculpe, não consegui gerar uma resposta agora."
    except Exception as e:
        answer = ("Ops! Tive um problema ao falar com o modelo. "
                "Tente de novo em alguns segundos. (Detalhe técnico ocultado)")

    # persiste histórico em memória
    history[chat_id].append({"role": "user", "content": text})
    history[chat_id].append({"role": "assistant", "content": answer})

    await send_message(chat_id, answer)
    return {"ok": True}
