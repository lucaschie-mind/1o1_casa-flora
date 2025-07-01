
from fastapi import FastAPI, Request, Response
from datetime import datetime
from models import async_session, Registro1o1
import os
from botbuilder.core import BotFrameworkAdapter, BotFrameworkAdapterSettings, TurnContext
from botbuilder.schema import Activity
from botbuilder.core.teams import TeamsInfo
from dateutil.parser import parse as parse_date
import requests

app = FastAPI()

APP_ID = os.getenv("MICROSOFT_APP_ID", "")
APP_PASSWORD = os.getenv("MICROSOFT_APP_PASSWORD", "")
SENDER_EMAIL = os.getenv("SENDER_EMAIL", "")
ACCESS_TOKEN = os.getenv("GRAPH_ACCESS_TOKEN", "")

adapter_settings = BotFrameworkAdapterSettings(APP_ID, APP_PASSWORD)
adapter = BotFrameworkAdapter(adapter_settings)

user_states = {}
user_responses = {}

questions = [
    "Qual será a data do 1:1? (formato: dd/mm/aaaa)",
    "Como você está se sentindo? \n\n1️⃣ - Nervoso(a)/Frustrado 😠\n\n2️⃣ - Triste 😢\n\n3️⃣ - Neutro(a) 😐\n\n4️⃣ - Feliz 🙂\n\n5️⃣ - Empolgado(a) 😄\n\n6️⃣ - Outro (Ansioso(a)/Preocupado(a)) 😟",
    "Fale um pouco mais de como está se sentindo.",
    "Quais as conquistas e avanços desde o último encontro?",
    "Quais os principais assuntos que serão discutidos no 1:1?",
    "Quais os combinados, alinhamentos e expectativas?"
]

sentimentos_map = {
    "1": "Nervoso(a)/Frustrado ",
    "2": "Triste",
    "3": "Neutro(a)",
    "4": "Feliz",
    "5": "Empolgado(a)",
    "6": "Outro (Ansioso(a)/Preocupado(a))",
    "nervoso": "Nervoso(a)/Frustrado",
    "triste": "Triste",
    "neutro": "Neutro(a)",
    "feliz": "Feliz",
    "empolgado": "Empolgado(a)",
    "outro": "Outro (Ansioso(a)/Preocupado(a))",
}

@app.get("/")
def root():
    return {"status": "ok"}

async def obter_email(turn_context):
    try:
        member = await TeamsInfo.get_member(turn_context, turn_context.activity.from_property.id)
        email = getattr(member, "email", None) or getattr(member, "user_principal_name", None)
        return email
    except Exception as e:
        print(f"Erro ao obter email: {e}")
        return None
    
def enviar_email(destinatario, assunto, corpo):
    url = f"https://graph.microsoft.com/v1.0/users/{SENDER_EMAIL}/sendMail"
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    email_data = {
        "message": {
            "subject": assunto,
            "body": {
                "contentType": "Text",
                "content": corpo
            },
            "toRecipients": [
                {"emailAddress": {"address": destinatario}}
            ]
        },
        "saveToSentItems": "true"
    }
    try:
        response = requests.post(url, headers=headers, json=email_data)
        if response.status_code == 202:
            print(f"✅ Email enviado para {destinatario}")
        else:
            print(f"❌ Erro ao enviar e-mail: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Exceção ao enviar e-mail: {e}")

async def on_turn(turn_context: TurnContext):
    text = turn_context.activity.text.strip()
    user_id = turn_context.activity.from_property.id
    user_name = turn_context.activity.from_property.name

    if user_id not in user_states:
        user_states[user_id] = 0
        user_responses[user_id] = []
        reply_text = f"Olá, {user_name}! Vamos começar. {questions[0]}"
    else:
        index = user_states[user_id]

        # Validação de data
        if index == 0:
            try:
                parsed_date = parse_date(text, dayfirst=True).date()
                user_responses[user_id].append(parsed_date)
            except Exception:
                await turn_context.send_activity("Data inválida. Por favor, envie no formato dd/mm/aaaa.")
                return
        # Validação do sentimento
        elif index == 1:
            text_lower = text.lower()
            mapped = None
            for key, value in sentimentos_map.items():
                if text_lower.startswith(key) or text_lower == value.lower():
                    mapped = value
                    break
            if mapped:
                user_responses[user_id].append(mapped)
            else:
                await turn_context.send_activity("Resposta inválida. Por favor escolha uma das opções de sentimento (1 a 6 ou o texto correspondente).")
                return
        else:
            user_responses[user_id].append(text)

        user_states[user_id] += 1

        if user_states[user_id] >= len(questions):
            user_email = await obter_email(turn_context)

             # Montagem do campo relatorio
            relatorio_text = f"""
Formulário 1:1

Data do 1:1:
{user_responses[user_id][0].strftime('%d/%m/%Y')}

Sentimento:
{user_responses[user_id][1]}

Comentário sobre o sentimento:
{user_responses[user_id][2]}

Conquistas:
{user_responses[user_id][3]}

Principais assuntos:
{user_responses[user_id][4]}

Combinados e expectativas:
{user_responses[user_id][5]}
"""


            try:
                async with async_session() as session:
                    novo_registro = Registro1o1(
                        nome_teams=user_name,
                        email_employee=user_email,
                        id_full=None,
                        nome_gestor=None,
                        email_gestor=None,
                        data_1o1=user_responses[user_id][0],
                        abertura=user_responses[user_id][1],
                        abertura_comentario=user_responses[user_id][2],
                        conquistas=user_responses[user_id][3],
                        principais_assuntos=user_responses[user_id][4],
                        combinados=user_responses[user_id][5],
                        datastamp=datetime.utcnow(),
                        relatorio=relatorio_text
                    )
                    session.add(novo_registro)
                    await session.commit()
                assunto = f"[Resumo semanal] - {user_responses[user_id][0].strftime('%d/%m/%Y')}"
                corpo = relatorio_text
                enviar_email(user_email, assunto, corpo)
                reply_text = "✅ Registro 1o1 salvo com sucesso!"
            except Exception as e:
                reply_text = f"❌ Erro ao salvar no banco: {e}"

            del user_states[user_id]
            del user_responses[user_id]
        else:
            reply_text = questions[user_states[user_id]]

    await turn_context.send_activity(reply_text)

@app.post("/api/messages")
async def messages(request: Request):
    body = await request.json()
    activity = Activity().deserialize(body)
    auth_header = request.headers.get("Authorization", "")

    async def aux_func(turn_context):
        await on_turn(turn_context)

    await adapter.process_activity(activity, auth_header, aux_func)
    return Response(status_code=200)
