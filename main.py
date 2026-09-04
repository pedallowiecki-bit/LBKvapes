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
GUILD_ID = os.getenv("GUILD_ID")        # ID serwera Discord (opcjonalnie dla szybkiej synchronizacji komend)

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
        elif res.status_code == 404:
            return [], None, None
        return [], None, f"Brak pliku products.json ({res.status_code})"
    except Exception as e:
        return [], None, str(e)

def update_github_file(products, commit_message):
    _, current_sha, _ = get_github_file()
    content_json = json.dumps(products, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')
    payload = {"message": commit_message, "content": encoded_content}
    if current_sha:
        payload["sha"] = current_sha
    res = requests.put(GITHUB_API_URL, headers=get_headers(), json=payload)
    return res.status_code in [200, 201]

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
    total = sum(item.get('price', 0) for item in cart_items)
    
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
        "total": total
    }
    orders.append(new_order)
    update_github_orders(orders, f"Nowe zamówienie {order_id} dla {discord_user}")

    if not bot.is_ready():
        return jsonify({"success": True, "order_id": order_id})

    target_guild_id = GUILD_ID
    if not target_guild_id and bot.guilds:
        target_guild_id = bot.guilds[0].id
    else:
        try:
            target_guild_id = int(target_guild_id)
        except:
            target_guild_id = None

    if target_guild_id:
        async def create_ticket_task():
            guild = bot.get_guild(target_guild_id)
            if not guild:
                return

            member = discord.utils.get(guild.members, name=discord_user) or discord.utils.get(guild.members, global_name=discord_user)
            
            channel_name = f"ticket-{discord_user}".lower().replace(" ", "-")
            channel_name = "".join(c for c in channel_name if c.isalnum() or c == "-")[:99]
            if not channel_name:
                channel_name = "ticket-zamowienie"

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            if member:
                overwrites[member] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

            embed = discord.Embed(title="🛒 Nowy Ticket Zamówienia", color=discord.Color.green())
            embed.add_field(name="👤 Klient", value=f"`{discord_user}` {member.mention if member else ''}", inline=True)
            embed.add_field(name="🆔 ID Zamówienia", value=f"`{order_id}`", inline=True)
            embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
            embed.add_field(name="📞 Telefon", value=f"`{phone}`", inline=True)
            embed.add_field(name="📦 Paczkomat", value=f"`{paczkomat}`", inline=False)
            
            items_str = "\n".join([f"- {i.get('title', i.get('name', 'Produkt'))} ({i.get('price', 0)} PLN)" for i in cart_items])
            embed.add_field(name="Produkty", value=items_str or "Brak", inline=False)
            embed.add_field(name="Suma", value=f"**{total} PLN**", inline=False)
            
            ping_content = member.mention if member else f"@{discord_user}"
            await ticket_channel.send(content=ping_content, embed=embed)

        asyncio.run_coroutine_threadsafe(create_ticket_task(), bot.loop)

    return jsonify({"success": True, "order_id": order_id})

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"✅ Bot jest ONLINE jako: {bot.user}")
    try:
        if GUILD_ID:
            guild_obj = discord.Object(id=int(GUILD_ID))
            bot.tree.copy_global_to(guild=guild_obj)
            synced = await bot.tree.sync(guild=guild_obj)
            print(f"🔄 Zsynchronizowano {len(synced)} komend dla serwera {GUILD_ID}!")
        else:
            synced = await bot.tree.sync()
            print(f"🔄 Zsynchronizowano globalnie {len(synced)} komend!")
    except Exception as e:
        print(f"❌ Błąd synchronizacji: {e}")

@bot.tree.command(name="sklep", description="Wyświetla aktualne produkty ze sklepu")
async def sklep(interaction: discord.Interaction):
    await interaction.response.defer()
    products, _, error = get_github_file()
    if error and "Brak pliku" not in error:
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

@bot.tree.command(name="dodaj", description="Dodaje nowy produkt do sklepu (tylko dla administracji)")
@app_commands.describe(nazwa="Nazwa produktu", cena="Cena w PLN", product_id="Unikalne ID produktu (opcjonalnie)")
@app_commands.default_permissions(administrator=True)
async def dodaj(interaction: discord.Interaction, nazwa: str, cena: float, product_id: str = None):
    await interaction.response.defer(ephemeral=True)
    
    products, _, error = get_github_file()
    if error and "Brak pliku" not in error and "404" not in error:
        await interaction.followup.send(f"❌ Błąd pobierania produktów z GitHuba: {error}", ephemeral=True)
        return
        
    if not isinstance(products, list):
        products = []
        
    if not product_id:
        product_id = 'PRD-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
        
    if any(str(p.get('id')).upper() == product_id.upper() for p in products):
        await interaction.followup.send(f"❌ Produkt o ID `{product_id}` już istnieje!", ephemeral=True)
        return
        
    new_product = {
        "id": product_id,
        "name": nazwa,
        "price": cena
    }
    
    products.append(new_product)
    success = update_github_file(products, f"Dodano produkt {nazwa} ({product_id}) przez Discord")
    
    if success:
        await interaction.followup.send(f"✅ Pomyślnie dodano produkt do sklepu!\n* **Nazwa:** {nazwa}\n* **Cena:** {cena} PLN\n* **ID:** `{product_id}`", ephemeral=True)
    else:
        await interaction.followup.send("❌ Błąd podczas zapisu produktu na GitHubie.", ephemeral=True)

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
    channel_name = "".join(c for c in channel_name if c.isalnum() or c == "-")[:99]

    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

    remaining_orders = [o for o in orders if str(o.get('id')).upper() != order_id.upper()]
    update_github_orders(remaining_orders, f"Zrealizowano zamówienie {order_id} przez komendę")

    await interaction.followup.send(f"✅ Otworzono ticket: {ticket_channel.mention}", ephemeral=True)

    embed = discord.Embed(title="🛒 Nowy Ticket Zamówienia", color=discord.Color.green())
    embed.add_field(name="👤 Klient", value=f"`{order.get('discord')}` {user.mention}", inline=True)
    embed.add_field(name="🆔 ID", value=f"`{order_id}`", inline=True)
    embed.add_field(name="📧 Email", value=f"`{order.get('email')}`", inline=True)
    embed.add_field(name="📞 Telefon", value=f"`{order.get('phone')}`", inline=True)
    embed.add_field(name="📦 Paczkomat", value=f"`{order.get('paczkomat')}`", inline=False)
    
    items_str = "\n".join([f"- {i.get('title', i.get('name', 'Produkt'))} ({i.get('price', 0)} PLN)" for i in items])
    embed.add_field(name="Produkty", value=items_str or "Brak", inline=False)
    embed.add_field(name="Suma", value=f"**{order.get('total')} PLN**", inline=False)
    
    await ticket_channel.send(content=user.mention, embed=embed)

@bot.tree.command(name="zamknij", description="Zamyka ticket")
async def zamknij(interaction: discord.Interaction):
    if "ticket-" in interaction.channel.name:
        await interaction.response.send_message("🔒 Zamykanie ticketu za 3 sekundy...")
        await asyncio.sleep(3)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("❌ Tylko na kanale ticketu.", ephemeral=True)

@bot.tree.command(name="rr", description="Restartuje bota i wysyła powiadomienie")
@app_commands.default_permissions(administrator=True)
async def rr(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Wykonuję restart bota i aplikacji...", ephemeral=True)
    
    restart_channel_id = 1545521609408905296
    try:
        channel = bot.get_channel(restart_channel_id) or await bot.fetch_channel(restart_channel_id)
        if channel:
            await channel.send("⚠️ **Bot przechodzi ponowny restart systemu (`/rr`).** Za chwilę wracam do trybu online!")
    except Exception as e:
        print(f"Nie udało się wysłać powiadomienia o restarcie: {e}")

    await asyncio.sleep(1)
    os._exit(0)

if __name__ == "__main__":
    threading.Thread(target=run_flask, daemon=True).start()
    bot.run(DISCORD_TOKEN)
