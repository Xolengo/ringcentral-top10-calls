import os
import requests
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

CLIENT_ID = os.getenv("RINGCENTRAL_CLIENT_ID")
CLIENT_SECRET = os.getenv("RINGCENTRAL_CLIENT_SECRET")
JWT = os.getenv("RINGCENTRAL_JWT")
CHAT_ID = os.getenv("RINGCENTRAL_CHAT_ID")
# ====================================
# AUTH
# ====================================
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
# ====================================
# FECHAS AYER
# ====================================
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
print(
    f"Consultando desde {ayer_inicio.isoformat()}"
)
print(
    f"Consultando hasta {ayer_fin.isoformat()}"
)
# ====================================
# EXTENSIONES (TODAS LAS PAGINAS)
# ====================================
ext_info = {}
page = 1
while True:
    response = requests.get(
        "https://platform.ringcentral.com/restapi/v1.0/account/~/extension",
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "perPage": 1000,
            "page": page
        }
    )
    response.raise_for_status()
    data = response.json()
    extensions = data.get(
        "records",
        []
    )
    if not extensions:
        break
    for ext in extensions:
        ext_id = str(ext["id"])
        contact = ext.get(
            "contact",
            {}
        )
        first_name = contact.get(
            "firstName",
            ""
        ).strip()
        last_name = contact.get(
            "lastName",
            ""
        ).strip()
        nombre_completo = (
            f"{first_name} {last_name}"
        ).strip()
        if not nombre_completo:
            nombre_completo = (
                ext.get("name")
                or f"Extension {ext_id}"
            )
        departamento = (
            contact.get("department")
            or "Sin departamento"
        )
        sitio = (
            ext.get("site", {})
            .get("name")
            or "Sin sitio"
        )
        ext_info[ext_id] = {
            "nombre": nombre_completo,
            "departamento": departamento,
            "sitio": sitio
        }
    print(
        f"Pagina extensiones {page}: {len(extensions)}"
    )

    if len(extensions) < 1000:
        break
    page += 1
print(
    f"Extensiones totales: {len(ext_info)}"
)
# ====================================
# CALL LOG
# ====================================
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
    registros = data.get(
        "records",
        []
    )
    calls.extend(registros)
    print(
        f"Pagina {page}: {len(registros)} llamadas"
    )
    if len(registros) < 1000:
        break
    page += 1
print(f"Total llamadas: {len(calls)}")
# ====================================
# KPIS POR USUARIO
# ====================================
ranking = defaultdict(
    lambda: {
        "total": 0,
        "connected": 0,
        "busy": 0,
        "no_answer": 0,
        "hang_up": 0,
        "wrong_number": 0,
        "call_failed": 0,
        "duration": 0,
        "inbound": 0,
        "outbound": 0
    }
)
global_inbound = 0
global_outbound = 0
for call in calls:
    ext_id = call.get(
        "from",
        {}
    ).get(
        "extensionId"
    )
    if not ext_id:
        direccion = call.get("direction", "")
        if direccion == "Inbound":
            global_inbound += 1
        elif direccion == "Outbound":
            global_outbound += 1
        continue
    ext_id = str(ext_id)
    resultado = call.get(
        "result",
        ""
    )
    direccion = call.get(
        "direction",
        ""
    )
    ranking[ext_id]["total"] += 1
    ranking[ext_id]["duration"] += call.get(
        "duration",
        0
    )
    if direccion == "Inbound":
        ranking[ext_id]["inbound"] += 1
        global_inbound += 1
    elif direccion == "Outbound":
        ranking[ext_id]["outbound"] += 1
        global_outbound += 1
    if resultado == "Call connected":
        ranking[ext_id]["connected"] += 1
    elif resultado == "Busy":
        ranking[ext_id]["busy"] += 1
    elif resultado == "No Answer":
        ranking[ext_id]["no_answer"] += 1
    elif resultado == "Hang Up":
        ranking[ext_id]["hang_up"] += 1
    elif resultado == "Wrong Number":
        ranking[ext_id]["wrong_number"] += 1
    elif resultado in [
        "Call Failed",
        "Call Failure"
    ]:
        ranking[ext_id]["call_failed"] += 1
# ====================================
# TOP 10
# ====================================
top10 = sorted(
    ranking.items(),
    key=lambda x: x[1]["total"],
    reverse=True
)[:10]
# ====================================
# KPI GLOBAL
# ====================================
global_connected = sum(
    x["connected"]
    for x in ranking.values()
)
global_duration = sum(
    x["duration"]
    for x in ranking.values()
)
agentes_activos = len(ranking)
promedio_llamadas = round(
    len(calls) / agentes_activos,
    1
) if agentes_activos > 0 else 0
# ====================================
# MENSAJE
# ====================================
mensaje = "🏆 TOP 10 LLAMADAS - AYER\n\n"
mejor_efectividad = {
    "nombre": "",
    "valor": 0
}
mayor_talktime = {
    "nombre": "",
    "valor": 0
}
for pos, (ext_id, datos) in enumerate(
    top10,
    start=1
):
    usuario = ext_info.get(
        ext_id,
        {}
    )
    nombre = usuario.get(
        "nombre",
        ext_id
    )
    departamento = usuario.get(
        "departamento",
        "Sin departamento"
    )
    sitio = usuario.get(
        "sitio",
        "Sin sitio"
    )
    efectividad = (
        datos["connected"]
        / datos["total"]
        * 100
        if datos["total"] > 0
        else 0
    )
    minutos = round(
        datos["duration"] / 60,
        1
    )
    if efectividad > mejor_efectividad["valor"]:
        mejor_efectividad["valor"] = efectividad
        mejor_efectividad["nombre"] = nombre
    if minutos > mayor_talktime["valor"]:
        mayor_talktime["valor"] = minutos
        mayor_talktime["nombre"] = nombre
    if pos == 1:
        mensaje += (
            "👑 CAMPEÓN DEL DÍA\n\n"
            f"{nombre}\n"
            f"📞 {datos['total']} llamadas\n"
            f"✅ {datos['connected']} conectadas\n"
            f"🎯 {efectividad:.1f}% efectividad\n"
            f"🕒 {minutos} min hablados\n\n"
        )
    mensaje += (
            f"#{pos} {nombre}\n"
            f"🏢 {departamento}\n"
            f"📍 {sitio}\n"
            f"📞 Total: {datos['total']}\n"
            f"⬅️ Inbound: {datos['inbound']}\n"
            f"➡️ Outbound: {datos['outbound']}\n"
            f"✅ Connected: {datos['connected']}\n"
            f"📴 Busy: {datos['busy']}\n"
            f"⏳ No Answer: {datos['no_answer']}\n"
            f"☎️ Hang Up: {datos['hang_up']}\n"
            f"❌ Wrong Number: {datos['wrong_number']}\n"
            f"🚨 Call Failed: {datos['call_failed']}\n"
            f"🕒 Talk Time: {minutos} min\n"
            f"🎯 Efectividad: {efectividad:.1f}%\n\n"
        )
mensaje += (
    "\n════════════════════\n"
    "🥇 RECONOCIMIENTOS DEL DÍA\n\n"
    f"📞 Mayor volumen: {top10[0][1]['total']} llamadas\n"
    f"👤 {ext_info.get(top10[0][0], {}).get('nombre', top10[0][0])}\n\n"
    f"🕒 Mayor Talk Time: {mayor_talktime['valor']} min\n"
    f"👤 {mayor_talktime['nombre']}\n\n"
    f"🎯 Mejor efectividad: {mejor_efectividad['valor']:.1f}%\n"
    f"👤 {mejor_efectividad['nombre']}\n"
)
# ====================================
# RESUMEN GLOBAL
# ====================================
contact_rate = (
    global_connected
    / len(calls)
    * 100
    if len(calls) > 0
    else 0
)
horas_globales = round(
    global_duration / 3600,
    1
)
mensaje += (
    "\n════════════════════\n"
    "📊 RESUMEN TENANT\n\n"
    f"👥 Agentes activos: {agentes_activos}\n"
    f"📈 Promedio por agente: {promedio_llamadas}\n"
    f"📞 Total Calls: {len(calls)}\n"
    f"⬅️ Inbound: {global_inbound}\n"
    f"➡️ Outbound: {global_outbound}\n"
    f"✅ Connected: {global_connected}\n"
    f"🎯 Contact Rate: {contact_rate:.1f}%\n"
    f"🕒 Talk Time: {horas_globales} hrs\n"
)
print(mensaje)
# ====================================
# ENVIAR CHAT
# ====================================
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
