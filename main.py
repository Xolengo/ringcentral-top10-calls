import os
import requests

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
JWT = os.getenv("RINGCENTRAL_JWT")
CHAT_ID = os.getenv("RINGCENTRAL_CHAT_ID")

# Token
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

print("TOKEN OK")

# Mensaje de prueba
mensaje = """
✅ GitHub Actions conectado.

Prueba de envío al chat RingCentral.

Proyecto:
ringcentral-top10-calls
"""

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

print(response.status_code)
print(response.text)

response.raise_for_status()

print("MENSAJE ENVIADO")
