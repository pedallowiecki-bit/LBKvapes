# main.py (Flask + Discord Bot w jednym pliku na Render.com)
import os
import json
import base64
import threading
import random
import string
import asyncio
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
import discord
from discord import app_commands
from discord.ext import commands

app = Flask(__name__)
CORS(app)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")  # np. nazwa-uzytkownika/nazwa-repo

FILE_PATH = "products.json"
ORDERS_FILE_PATH = "orders.json"

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
ORDERS_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ORDERS_FILE_PATH}"

def get_headers():
    token = GITHUB_TOKEN.strip() if GITHUB_TOKEN else ""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DiscordBot-LBK"
    }

def get_github_file():
    try:
        res = requests.get(GITHUB_API_URL, headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            file_res = requests.get(data.get('download_url'), headers={"User-Agent": "DiscordBot-LBK"})
            return json.loads(file_res.text), data.get('sha'), None
        return [], None, "Brak pliku products.json"
    except Exception as e:
        return [], None, str(e)

def get_github_orders():
    try:
        res = requests.get(ORDERS_GITHUB_API_URL, headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            file_res = requests.get(data.get('download_url'), headers={"User-Agent": "DiscordBot-LBK"})
            return json.loads(file_res.text), data.get('sha'), None
        elif res.status_code == 404:
            return [], None, None
        return [], None, f"Error: {res.status_code}"
    except Exception as e:
        return [], None, str(e)

def update_github_orders(orders, commit_message):
    _, current_sha, _ = get_github_orders()
    content_json = json.dumps(orders, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')
    payload = {"message": commit_message, "content": encoded_content}
    if current_sha:
        payload["sha"] = current_sha
    res = requests.put(ORDERS_GITHUB_API_URL, headers=get_headers(), json=payload)
    return res.status_code in [200, 201]

@app.route("/", methods=["GET"])
def home():
    return "Bot and Web Server are ONLINE", 200

@app.route("/create-order", methods=["POST", "OPTIONS"])
def create_order():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    
    data = request.json
    if not data:
        return jsonify({"success": False, "error": "Brak danych"}), 400

    discord_user = data.get('discord', '').strip()
    email = data.get('email', '').strip()
    phone = data.get('phone', '').strip()
    paczkomat = data.get('paczkomat', '').strip()
    cart_items = data.get('items', [])

    if not discord_user or not cart_items:
        return jsonify({"success": False, "error": "Brak wymaganych danych lub pusty koszyk"}), 400

    order_id = 'LBK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    orders, _, _ = get_github_orders()
    if not isinstance(orders, list):
        orders = []

    new_order = {
        "id": order_id,
        "discord": discord_user,
        "email": email,
        "phone": phone,
        "paczkomat": paczkomat,
        "items": cart_items,
        "total": sum(item.get('price', 0) for item in cart_items)
    }
    orders.append(new_order)

    success = update_github_orders(orders, f"Nowe zamówienie {order_id} dla {discord_user}")

    if success:
        return jsonify({"success": True, "order_id": order_id})
    else:
        return jsonify({"success": False, "error": "Błąd zapisu na GitHubie"}), 500

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot jest ONLINE jako: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Zsynchronizowano {len(synced)} komend!")
    except Exception as e:
        print(f"❌ Błąd synchronizacji: {e}")

@bot.tree.command(name="sklep", description="Wyświetla aktualne produkty ze sklepu")
async def sklep(interaction: discord.Interaction):
    await interaction.response.defer()
    products, _, error = get_github_file()
    if error:
        await interaction.followup.send(f"❌ {error}")
        return
    if not products:
        await interaction.followup.send("🛍️ Sklep jest obecnie pusty.")
        return

    embed = discord.Embed(title="🛍️ Oferta Sklepu LBKPETS", color=discord.Color.blue())
    for p in products:
        price = p.get('price', 0)
        embed.add_field(name=p.get('name'), value=f"Cena: **{price} PLN**\nID: `{p.get('id')}`", inline=False)
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="zamowienie", description="Otwórz ticket na podstawie ID zamówienia")
@app_commands.describe(order_id="ID zamówienia z koszyka np. LBK-XXXXX")
async def zamowienie(interaction: discord.Interaction, order_id: str):
    await interaction.response.defer(ephemeral=True)
    orders, _, error = get_github_orders()
    order = next((o for o in orders if str(o.get('id')).upper() == order_id.upper()), None)
    if not order:
        await interaction.followup.send(f"❌ Nie znaleziono zamówienia o ID `{order_id}`.", ephemeral=True)
        return

    guild = interaction.guild
    user = interaction.user
    items = order.get('items', [])
    
    channel_name = f"ticket-{user.name}".lower().replace(" ", "-")
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

    remaining_orders = [o for o in orders if str(o.get('id')).upper() != order_id.upper()]
    update_github_orders(remaining_orders, f"Zrealizowano zamówienie {order_id}")

    await interaction.followup.send(f"✅ Otworzono ticket: {ticket_channel.mention}", ephemeral=True)

    embed = discord.Embed(title="🛒 Nowy Ticket Zamówienia", color=discord.Color.green())
    embed.add_field(name="👤 Klient", value=f"`{order.get('discord')}`", inline=True)
    embed.add_field(name="🆔 ID", value=f"`{order_id}`", inline=True)
    embed.add_field(name="📧 Email", value=f"`{order.get('email')}`", inline=True)
    embed.add_field(name="📞 Telefon", value=f"`{order.get('phone')}`", inline=True)
    embed.add_field(name="📦 Paczkomat", value=f"`{order.get('paczkomat')}`", inline=False)
    
    items_str = "\n".join([f"- {i.get('title')} ({i.get('price')} PLN)" for i in items])
    embed.add_field(name="Produkty", value=items_str or "Brak", inline=False)
    embed.add_field(name="Suma", value=f"**{order.get('total')} PLN**", inline=False)
    
    await ticket_channel.send(content=f"{user.mention}", embed=embed)

@bot.tree.command(name="zamknij", description="Zamyka ticket")
async def zamknij(interaction: discord.Interaction):
    if "ticket-" in interaction.channel.name:
        await interaction.response.send_message("🔒 Zamykanie ticketu za 3 sekundy...")
        await asyncio.sleep(3)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("❌ Tylko na kanale ticketu.", ephemeral=True)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
