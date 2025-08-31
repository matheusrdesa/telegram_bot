# Telegram LLM Bot (FastAPI + Groq)

Um starter simples para rodar um bot do Telegram usando FastAPI e um LLM gratuito no Groq (compatível com OpenAI).

## 0) Pré-requisitos (contas gratuitas)
- Telegram (para falar com o @BotFather e criar seu bot)
- GitHub (para hospedar este código)
- Render.com (para deploy gratuito do web service)
- Groq Cloud (para obter a GROQ_API_KEY)

## 1) Crie seu bot no Telegram
1. Abra o Telegram e fale com **@BotFather**.
2. Envie `/newbot` e siga as instruções (escolha nome e **username** que termina em `bot`).
3. Ao final, copie o **BOT TOKEN** (formato `123456789:ABC-...`). **Guarde**.
4. Opcional: em `/setprivacy` você pode ajustar o modo de privacidade conforme o uso.

## 2) Crie a sua chave do Groq
1. Acesse o painel do Groq Cloud e gere uma **API Key**.
2. Guarde o valor como `GROQ_API_KEY`. O modelo default usado aqui é `llama-3.1-8b-instant`.

## 3) Baixe este projeto e suba no GitHub
- Você pode fazer upload do zip no seu repositório GitHub **(não inclua `.env`)**.

### Estrutura
```
.
├── main.py
├── requirements.txt
├── render.yaml
├── set_webhook.sh
└── .env.example
```

## 4) Deploy na Render (plano free)
1. **New +** → **Web Service** → **Build & deploy from a Git repo** → selecione seu repo.
2. Build Command: `pip install -r requirements.txt`
3. Start Command: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Configure **Environment Variables**:
   - `TELEGRAM_TOKEN`: o token do BotFather
   - `GROQ_API_KEY`: sua chave do Groq
   - `MODEL_ID`: (opcional) por ex.: `llama-3.1-8b-instant`
   - `WEBHOOK_SECRET`: um segredo curto (ex.: `minha_chave_123`)

> Dica: o arquivo `render.yaml` já sugere um serviço `env: python` plano `free`; pode usar interface gráfica sem YAML também.

## 5) Configure o webhook do Telegram
Depois que seu serviço estiver **live**, rode (no seu terminal):
```bash
export TELEGRAM_TOKEN=xxxx:yyyy
export PUBLIC_URL=https://SEU-SERVICO.onrender.com
export WEBHOOK_SECRET=um_segredo_curto

curl -X POST "https://api.telegram.org/bot$TELEGRAM_TOKEN/setWebhook"   -d url="$PUBLIC_URL/webhook/$TELEGRAM_TOKEN"   -d secret_token="$WEBHOOK_SECRET"
```
Ou use `./set_webhook.sh` (lembre de `chmod +x set_webhook.sh`).

## 6) Teste
- No Telegram, abra o chat do seu bot e envie `/start`.
- Envie perguntas livres. Use `/help` e `/reset` quando precisar.

## 7) Notas
- Não commite segredos (tokens/keys). Use variáveis de ambiente na Render.
- Este starter mantém **histórico em memória** (reinicia ao fazer deploy/restart). Para produção, considere armazenar histórico em Redis/DB.
- Para respeitar limites, evite bursts de mensagens; implemente fila/backoff se necessário.
