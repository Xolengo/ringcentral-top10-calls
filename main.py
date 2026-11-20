import os
import requests

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
JWT = os.getenv("RINGCENTRAL_JWT")
CHAT_ID = os.getenv("RINGCENTRAL_CHAT_ID")

# TOKEN

response = requests.post(
    "https://platform.ringcentral.com/restapi/oauth/token",
    auth=(CLIENT_ID, CLIENT_SECRET),
    headers={
        "Content-Type": "application/x-www-form-urlencoded"
    },
    data={
        "grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer",
        "assertion": JWT
    }
)

response.raise_for_status()

access_token = response.json()["access_token"]

# AYER

tz = ZoneInfo("America/Mexico_City")

hoy = datetime.now(tz)

ayer_inicio = (
    hoy - timedelta(days=1)
).replace(
    hour=0,
    minute=0,
    second=0,
    microsecond=0
)

ayer_fin = ayer_inicio + timedelta(days=1)

# OBTENER EXTENSIONES

response = requests.get(
    "https://platform.ringcentral.com/restapi/v1.0/account/~/extension",
    headers={
        "Authorization": f"Bearer {access_token}"
    }
)

response.raise_for_status()

extensions = response.json()["records"]

ext_names = {}

for ext in extensions:
    ext_names[str(ext["id"])] = ext.get(
        "name",
        f"Extension {ext['id']}"
    )

# CALL LOG

calls = []
page = 1

while True:

    response = requests.get(
        "https://platform.ringcentral.com/restapi/v1.0/account/~/call-log",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "view": "Detailed",
            "dateFrom": ayer_inicio.isoformat(),
            "dateTo": ayer_fin.isoformat(),
            "perPage": 1000,
            "page": page
        }
    )

    response.raise_for_status()

    data = response.json()

    registros = data.get("records", [])

    calls.extend(registros)

    if len(registros) < 1000:
        break

    page += 1

# CONTAR POR EXTENSION

ranking = defaultdict(int)

for call in calls:

    ext_id = call.get(
        "from",
        {}
    ).get(
        "extensionId"
    )

    if ext_id:
        ranking[str(ext_id)] += 1

# TOP 10

top10 = sorted(
    ranking.items(),
    key=lambda x: x[1],
    reverse=True
)[:10]

# MENSAJE

mensaje = "🏆 TOP 10 LLAMADAS - AYER\n\n"

for pos, (ext_id, total) in enumerate(top10, start=1):

    nombre = ext_names.get(
        ext_id,
        ext_id
    )

    mensaje += (
        f"{pos}. {nombre}\n"
        f"📞 {total} llamadas\n\n"
    )

mensaje += f"📊 Total Tenant: {len(calls)} llamadas"

# ENVIAR A CHAT

response = requests.post(
    f"https://platform.ringcentral.com/restapi/v1.0/glip/chats/{CHAT_ID}/posts",
    headers={
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json"
    },
    json={
        "text": mensaje
    }
)

response.raise_for_status()

print("TOP10 ENVIADO")
