import os
import json
import base64
import requests
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
from discord import app_commands

# ID RÓL Z DISCORDA
ADMIN_ROLE_ID = 1518638158961709153
CLIENT_ROLE_ID = 1518633914925580438

# KONFIGURACJA ZMIENNYCH ŚRODOWISKOWYCH
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # np. "TwojNick/lbkpets-store"
FILE_PATH = "products.json"

# SERWER HTTP DLA RENDERA (Zapobiega błędom i wyłączaniu usłu)
class KeepAliveHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"LBKPETS Bot is running 24/7!")

def run_http_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), KeepAliveHandler)
    print(f"🌐 Serwer HTTP dla Rendera uruchomiony na porcie {port}")
    server.serve_forever()

# Uruchomienie serwera HTTP w osobnym wątku
threading.Thread(target=run_http_server, daemon=True).start()

# INTENTY BOTA DISCORD
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

def update_github_json(new_products, commit_msg):
    url = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
    headers = {
        "Authorization": f"token {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json"
    }
    
    res = requests.get(url, headers=headers)
    sha = res.json().get("sha", "") if res.status_code == 200 else ""
    
    content_str = json.dumps(new_products, indent=2, ensure_ascii=False)
    content_b64 = base64.b64encode(content_str.encode("utf-8")).decode("utf-8")
    
    payload = {
        "message": f"🤖 {commit_msg}",
        "content": content_b64,
        "sha": sha
    }
    
    put_res = requests.put(url, headers=headers, json=payload)
    return put_res.status_code in [200, 201]

def get_current_products():
    raw_url = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{FILE_PATH}"
    res = requests.get(raw_url)
    return res.json() if res.status_code == 200 else []

@bot.event
async def on_ready():
    print(f"✅ Bot zalogowany jako {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"⚡ Zsynchronizowano {len(synced)} komend slash.")
    except Exception as e:
        print(f"Błąd synchronizacji: {e}")

# =========================================================
# KOMENDY DLA ADMINA (Rola ID: 1518638158961709153)
# =========================================================

@bot.tree.command(name="dodaj", description="[ADMIN] Dodaj nowy produkt do sklepu")
@app_commands.describe(
    nazwa="Nazwa produktu",
    cena="Cena w PLN",
    obrazek="URL do zdjęcia",
    stara_cena="Opcjonalna stara cena",
    badge="Opcjonalna plakietka (np. HOT 🔥)"
)
async def dodaj(
    interaction: discord.Interaction, 
    nazwa: str, 
    cena: float, 
    obrazek: str, 
    stara_cena: float = None, 
    badge: str = None
):
    user_role_ids = [role.id for role in interaction.user.roles]
    if ADMIN_ROLE_ID not in user_role_ids:
        await interaction.response.send_message("❌ Ta komenda jest zarezerwowana tylko dla Admina!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    products = get_current_products()

    nowy_produkt = {
        "id": int(interaction.id),
        "name": nazwa,
        "price": cena,
        "oldPrice": stara_cena,
        "badge": badge,
        "img": obrazek
    }
    products.append(nowy_produkt)

    if update_github_json(products, f"Dodano produkt: {nazwa}"):
        embed = discord.Embed(title="✅ Dodano Nowy Produkt!", color=0x00a6ff)
        embed.add_field(name="Nazwa", value=nazwa, inline=False)
        embed.add_field(name="Cena", value=f"{cena:.2f} PLN", inline=True)
        if stara_cena:
            embed.add_field(name="Stara Cena", value=f"{stara_cena:.2f} PLN", inline=True)
        if badge:
            embed.add_field(name="Plakietka", value=badge, inline=True)
        embed.set_thumbnail(url=obrazek)
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send("❌ Błąd zapisu w GitHubie.")

@bot.tree.command(name="usun", description="[ADMIN] Usuń produkt ze sklepu po ID")
async def usun(interaction: discord.Interaction, product_id: str):
    user_role_ids = [role.id for role in interaction.user.roles]
    if ADMIN_ROLE_ID not in user_role_ids:
        await interaction.response.send_message("❌ Brak uprawnień admina!", ephemeral=True)
        return

    await interaction.response.defer(thinking=True)
    products = get_current_products()
    new_products = [p for p in products if str(p.get("id")) != product_id]

    if len(products) == len(new_products):
        await interaction.followup.send("❌ Nie znaleziono produktu o podanym ID.")
        return

    if update_github_json(new_products, f"Usunięto produkt ID: {product_id}"):
        await interaction.followup.send(f"🗑️ Pomyślnie usunięto produkt o ID: `{product_id}`")
    else:
        await interaction.followup.send("❌ Błąd zapisu w GitHubie.")

# =========================================================
# KOMENDY DLA KLIENTA (Rola ID: 1518633914925580438)
# =========================================================

@bot.tree.command(name="sklep", description="[KLIENT] Przeglądaj aktualną ofertę sklepu")
async def sklep(interaction: discord.Interaction):
    user_role_ids = [role.id for role in interaction.user.roles]
    if CLIENT_ROLE_ID not in user_role_ids and ADMIN_ROLE_ID not in user_role_ids:
        await interaction.response.send_message("❌ Nie posiadasz rangi Klienta!", ephemeral=True)
        return

    products = get_current_products()
    if not products:
        await interaction.response.send_message("🛒 Sklep jest obecnie pusty.", ephemeral=True)
        return

    embed = discord.Embed(title="🛍️ Oferta Sklepu LBKPETS", color=0x00a6ff)
    for p in products[:10]:
        cena_str = f"{p['price']:.2f} PLN"
        if p.get('oldPrice'):
            cena_str += f" ~({p['oldPrice']:.2f} PLN)~"
        embed.add_field(
            name=f"{p.get('badge', '')} {p['name']}".strip(),
            value=f"Cena: **{cena_str}** | ID: `{p['id']}`",
            inline=False
        )

    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="zamowienie", description="[KLIENT] Złóż zamówienie wpisując ID koszyka ze strony")
async def zamowienie(interaction: discord.Interaction, id: str):
    user_role_ids = [role.id for role in interaction.user.roles]
    if CLIENT_ROLE_ID not in user_role_ids and ADMIN_ROLE_ID not in user_role_ids:
        await interaction.response.send_message("❌ Brak wymaganej rangi Klienta!", ephemeral=True)
        return

    await interaction.response.send_message(
        f"📦 Dziękujemy za złożenie zamówienia `{id}`! Administracja skontaktuje się z Tobą na PW w celu finalizacji płatności.",
        ephemeral=True
    )

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ BŁĄD: Brak zmiennej DISCORD_TOKEN w Environment Variables!")
