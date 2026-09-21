Oto w pełni kompletny, gotowy do wklejenia kod do pliku main.py.
Wprowadziłem poprawki w strukturze uruchamiania, aby Flask i bot Discord działały stabilnie w jednym skrypcie na Render.com, bez konfliktów z pętlą asynchroniczną i bez żadnego Cloudflare – wszystko opiera się bezpośrednio na adresie Twojej aplikacji z Render.
Poprawiony plik main.py:
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
from werkzeug.security import generate_password_hash, check_password_hash
import discord
from discord import app_commands
from discord.ext import commands

app = Flask(__name__)
CORS(app)

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")
GUILD_ID = os.getenv("GUILD_ID")

CLIENT_ROLE_ID = "1545554046230855870"

FILE_PATH = "products.json"
ORDERS_FILE_PATH = "orders.json"
PROMOS_FILE_PATH = "promos.json"
REVIEWS_FILE_PATH = "reviews.json"
TRACKING_FILE_PATH = "tracking.json"
USERS_FILE_PATH = "users.json"

GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"
ORDERS_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{ORDERS_FILE_PATH}"
PROMOS_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{PROMOS_FILE_PATH}"
REVIEWS_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{REVIEWS_FILE_PATH}"
TRACKING_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{TRACKING_FILE_PATH}"
USERS_GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{USERS_FILE_PATH}"

DEFAULT_PRODUCTS = [
    {
        "id": "VAPE-001",
        "type": "Inne",
        "name": "ELFBAR ICE KING SUMMER 40k",
        "price": 88.0,
        "oldPrice": 100.0,
        "badge": "Bestseller",
        "img": "https://www.vapes24h.net/api/uploads/1780853828329-376936261.png",
        "smaki": [
            "Watermelon Ice", "Strawberry Kiwi", "Blueberry Ice", "Peach Mango", 
            "Blue Razz Lemonade", "Strawberry Watermelon", "Cherry Cola", "Double Apple", "Kiwi Passion Fruit Guava"
        ]
    },
    {
        "id": "SNUS-001",
        "type": "snus",
        "name": "CUBA BLACK LINE ULTRA",
        "price": 25.0,
        "oldPrice": None,
        "badge": "Nowość",
        "img": "https://vapespot.pl/_next/image?url=https%3A%2F%2Fi.imgur.com%2FbB5ZytT.png&w=640&q=75",
        "smaki": [
            "Cherry", "Pineapple", "Strong Mint", "Blackberry", 
            "Cool Mint", "Double Freeze", "Blueberry", "Forest Berries", "Lemonade"
        ]
    }
]

def get_headers():
    token = GITHUB_TOKEN.strip() if GITHUB_TOKEN else ""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DiscordBot-LBK"
    }

def get_github_json(api_url, default_value):
    try:
        res = requests.get(api_url, headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            sha = data.get('sha')
            content_b64 = data.get('content', '')
            content_bytes = base64.b64decode(content_b64.replace('\n', ''))
            content = json.loads(content_bytes.decode('utf-8'))
            if not content and default_value is not None:
                return default_value, sha, None
            return content, sha, None
        elif res.status_code == 404:
            return default_value, None, None
        return default_value, None, f"Error: {res.status_code}"
    except Exception as e:
        return default_value, None, str(e)

def update_github_json(api_url, data_obj, commit_message):
    _, current_sha, _ = get_github_json(api_url, None)
    content_json = json.dumps(data_obj, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')
    payload = {"message": commit_message, "content": encoded_content}
    if current_sha:
        payload["sha"] = current_sha
    res = requests.put(api_url, headers=get_headers(), json=payload)
    return res.status_code in [200, 201]

def get_github_file():
    return get_github_json(GITHUB_API_URL, DEFAULT_PRODUCTS)

def update_github_file(products, commit_message):
    return update_github_json(GITHUB_API_URL, products, commit_message)

def get_github_orders():
    return get_github_json(ORDERS_GITHUB_API_URL, [])

def update_github_orders(orders, commit_message):
    return update_github_json(ORDERS_GITHUB_API_URL, orders, commit_message)

def get_github_promos():
    return get_github_json(PROMOS_GITHUB_API_URL, {})

def update_github_promos(promos, commit_message):
    return update_github_json(PROMOS_GITHUB_API_URL, promos, commit_message)

def get_github_reviews():
    return get_github_json(REVIEWS_GITHUB_API_URL, [])

def update_github_reviews(reviews, commit_message):
    return update_github_json(REVIEWS_GITHUB_API_URL, reviews, commit_message)

def get_github_tracking():
    return get_github_json(TRACKING_GITHUB_API_URL, {})

def update_github_tracking(tracking_data, commit_message):
    return update_github_json(TRACKING_GITHUB_API_URL, tracking_data, commit_message)

def get_github_users():
    return get_github_json(USERS_GITHUB_API_URL, [])

def update_github_users(users, commit_message):
    return update_github_json(USERS_GITHUB_API_URL, users, commit_message)

@app.route("/", methods=["GET"])
def home():
    return "Bot and Web Server are ONLINE", 200

@app.route("/products", methods=["GET", "OPTIONS"])
def products_endpoint():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    products, _, _ = get_github_file()
    if not isinstance(products, list):
        products = DEFAULT_PRODUCTS
    return jsonify({"success": True, "products": products}), 200

@app.route("/reviews", methods=["GET", "OPTIONS"])
def reviews_endpoint():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    reviews, _, _ = get_github_reviews()
    if not isinstance(reviews, list):
        reviews = []
    return jsonify({"success": True, "reviews": reviews}), 200

@app.route("/check-promo", methods=["POST", "OPTIONS"])
def check_promo():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych"}), 400
    
    code = str(data.get('code', '')).strip().upper()
    promos, _, _ = get_github_promos()
    if not isinstance(promos, dict):
        promos = {}
        
    if code in promos:
        return jsonify({"success": True, "discount": promos[code]})
    return jsonify({"success": False, "error": "Nie znaleziono takiego kodu rabatowego"}), 404

@app.route("/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych"}), 400
    
    username = str(data.get('username', '')).strip()
    email = str(data.get('email', '')).strip().lower()
    password = str(data.get('password', '')).strip()
    
    if not username or not email or not password:
        return jsonify({"success": False, "error": "Wszystkie pola są wymagane"}), 400
        
    users, _, _ = get_github_users()
    if not isinstance(users, list):
        users = []
        
    for u in users:
        if u.get('email') == email or u.get('username', '').lower() == username.lower():
            return jsonify({"success": False, "error": "Konto o takim emailu lub nazwie już istnieje"}), 400
            
    hashed_pw = generate_password_hash(password)
    users.append({
        "username": username,
        "email": email,
        "password": hashed_pw
    })
    
    success = update_github_users(users, f"Rejestracja stałego konta: {username}")
    if success:
        return jsonify({"success": True}), 200
    return jsonify({"success": False, "error": "Błąd zapisu na GitHubie"}), 500

@app.route("/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych"}), 400
        
    identifier = str(data.get('identifier', '')).strip().lower()
    password = str(data.get('password', '')).strip()
    
    if not identifier or not password:
        return jsonify({"success": False, "error": "Wszystkie pola są wymagane"}), 400
        
    users, _, _ = get_github_users()
    if not isinstance(users, list):
        users = []
        
    user = None
    for u in users:
        if u.get('email', '').lower() == identifier or u.get('username', '').lower() == identifier:
            user = u
            break
            
    if not user or not check_password_hash(user['password'], password):
        return jsonify({"success": False, "error": "Nieprawidłowy login lub hasło"}), 401
        
    return jsonify({"success": True, "username": user['username'], "email": user['email']}), 200

@app.route("/create-order", methods=["POST", "OPTIONS"])
def create_order():
    if request.method == "OPTIONS":
        return jsonify({}), 200
    
    data = request.get_json(force=True, silent=True)
    if not data:
        return jsonify({"success": False, "error": "Brak danych lub nieprawidłowy format JSON"}), 400

    discord_user = str(data.get('discord', '')).strip()
    email = str(data.get('email', '')).strip()
    phone = str(data.get('phone', '')).strip()
    paczkomat = str(data.get('paczkomat', '')).strip()
    cart_items = data.get('items', [])

    if not discord_user or not cart_items:
        return jsonify({"success": False, "error": "Brak wymaganych danych lub pusty koszyk"}), 400

    order_id = 'LBK-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    items_total = sum(float(item.get('price', 0)) for item in cart_items)
    shipping_fee = 25.0
    total = items_total + shipping_fee
    
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
        "shipping": shipping_fee,
        "total": total,
        "payment": "Pobranie (Paczkomat)"
    }
    orders.append(new_order)
    update_github_orders(orders, f"Nowe zamówienie {order_id} dla {discord_user}")

    tracking_data, _, _ = get_github_tracking()
    if not isinstance(tracking_data, dict):
        tracking_data = {}
    tracking_data[order_id] = {
        "status": "Zamówienie przyjęte do realizacji (Import w toku)",
        "discord": discord_user
    }
    update_github_tracking(tracking_data, f"Utworzono status śledzenia dla {order_id}")

    if GUILD_ID and bot.is_ready():
        async def create_order_channel():
            try:
                guild = bot.get_guild(int(GUILD_ID))
                if not guild:
                    guild = await bot.fetch_guild(int(GUILD_ID))
                if not guild:
                    return

                channel_name = f"zamowienie-{order_id}".lower()
                channel_name = "".join(c for c in channel_name if c.isalnum() or c == "-")[:99]

                overwrites = {
                    guild.default_role: discord.PermissionOverwrite(read_messages=False),
                    guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
                }
                
                admin_roles = [r for r in guild.roles if r.permissions.administrator and r != guild.default_role]
                for r in admin_roles:
                    overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

                ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)

                customer_member = None
                try:
                    customer_member = guild.get_member_named(discord_user)
                    if not customer_member:
                        for m in guild.members:
                            if m.name.lower() == discord_user.lower() or (m.global_name and m.global_name.lower() == discord_user.lower()):
                                customer_member = m
                                break
                except Exception as e:
                    print(f"⚠️ Problem przy szukaniu użytkownika: {e}")

                if customer_member and CLIENT_ROLE_ID:
                    try:
                        client_role = guild.get_role(int(CLIENT_ROLE_ID))
                        if client_role:
                            await customer_member.add_roles(client_role)
                    except Exception as e:
                        print(f"❌ Błąd nadawania roli klienta: {e}")

                embed = discord.Embed(title="🛒 Nowe Zamówienie (Za pobraniem)", color=discord.Color.green())
                embed.add_field(name="👤 Klient", value=f"`{discord_user}` {customer_member.mention if customer_member else ''}", inline=True)
                embed.add_field(name="🆔 ID", value=f"`{order_id}`", inline=True)
                embed.add_field(name="📧 Email", value=f"`{email}`", inline=True)
                embed.add_field(name="📞 Telefon", value=f"`{phone}`", inline=True)
                embed.add_field(name="📦 Paczkomat / Płatność", value=f"`{paczkomat}`\nMetoda: **Pobranie**", inline=False)
                
                items_desc = []
                for i in cart_items:
                    title = i.get('title', i.get('name', 'Produkt'))
                    price = i.get('price', 0)
                    taste = i.get('selectedTaste', i.get('smak', 'Brak'))
                    items_desc.append(f"• **{title}** | Smak: `{taste}` | **{price} PLN**")

                embed.add_field(name="Produkty", value="\n".join(items_desc) or "Brak", inline=False)
                embed.add_field(name="Suma (z dostawą 25 zł)", value=f"**{total} PLN**", inline=False)
                
                ping_content = " ".join([r.mention for r in admin_roles]) if admin_roles else "@here"
                await ticket_channel.send(content=ping_content, embed=embed)
            except Exception as e:
                print(f"❌ [DISCORD KRYTYCZNY BŁĄD]: {e}")

        asyncio.run_coroutine_threadsafe(create_order_channel(), bot.loop)

    return jsonify({"success": True, "order_id": order_id}), 200

intents = discord.Intents.default()
intents.members = True
intents.guilds = True
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

class ReviewModal(discord.ui.Modal, title="Oceń nasz sklep"):
    ocena = discord.ui.TextInput(
        label="Ocena (liczba od 1 do 5)",
        placeholder="np. 5",
        max_length=1,
        required=True
    )
    opinia = discord.ui.TextInput(
        label="Twoja opinia o zakupach",
        style=discord.TextStyle.paragraph,
        placeholder="Napisz kilka zdań o obsłudze i produktach...",
        required=True
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.send_message("✅ Twoja opinia została przesłana do weryfikacji przez administrację!", ephemeral=True)
        admin_channel = interaction.channel

        embed = discord.Embed(title="⭐ Nowa Opinia do Weryfikacji", color=discord.Color.gold())
        embed.add_field(name="👤 Użytkownik", value=interaction.user.mention, inline=True)
        embed.add_field(name="🌟 Ocena", value=f"`{self.ocena.value} / 5`", inline=True)
        embed.add_field(name="💬 Treść opinii", value=self.opinia.value, inline=False)

        view = AdminReviewView(interaction.user.name, self.ocena.value, self.opinia.value)
        if admin_channel:
            await admin_channel.send(embed=embed, view=view)

class ReviewButtonView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📝 Oceń sklep", style=discord.ButtonStyle.green, custom_id="open_review_modal_btn")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        has_role = any(str(r.id) == CLIENT_ROLE_ID for r in interaction.user.roles) if isinstance(interaction.user, discord.Member) else False
        if not has_role:
            await interaction.response.send_message("❌ Opinie mogą wystawiać tylko zweryfikowani klienci!", ephemeral=True)
            return
        await interaction.response.send_modal(ReviewModal())

class AdminReviewView(discord.ui.View):
    def __init__(self, user_name, ocena, opinia):
        super().__init__(timeout=None)
        self.user_name = user_name
        self.ocena = ocena
        self.opinia = opinia

    @discord.ui.button(label="Zaakceptuj", style=discord.ButtonStyle.green, custom_id="accept_review_btn")
    async def accept(self, interaction: discord.Interaction, button: discord.ui.Button):
        reviews, _, _ = get_github_reviews()
        if not isinstance(reviews, list):
            reviews = []
        
        new_review = {
            "user": self.user_name,
            "rating": self.ocena,
            "comment": self.opinia
        }
        reviews.append(new_review)
        update_github_reviews(reviews, f"Zaakceptowano opinię od {self.user_name}")

        for child in self.children:
            child.disabled = True
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Zaakceptowana Opinia Sklepu"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("✅ Opinia została zaakceptowana i zapisana!", ephemeral=True)

    @discord.ui.button(label="Odrzuć", style=discord.ButtonStyle.red, custom_id="reject_review_btn")
    async def reject(self, interaction: discord.Interaction, button: discord.ui.Button):
        for child in self.children:
            child.disabled = True
            
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Odrzucona Opinia Sklepu"
        await interaction.message.edit(embed=embed, view=self)
        await interaction.response.send_message("❌ Opinia została odrzucona.", ephemeral=True)

@bot.event
async def on_ready():
    print(f"✅ Bot jest ONLINE jako: {bot.user}")
    bot.add_view(ReviewButtonView())
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

@bot.tree.command(name="sklep", description="Wyświetla pełną ofertę sklepu")
async def sklep(interaction: discord.Interaction):
    await interaction.response.defer()
    products, _, error = get_github_file()
    
    if error and "Brak pliku" not in error:
        await interaction.followup.send(f"❌ Błąd: {error}")
        return
    if not products:
        await interaction.followup.send("🛍️ Sklep jest obecnie pusty.")
        return

    embed = discord.Embed(title="🛍️ Oferta Sklepu LBK", color=discord.Color.blue())
    for p in products:
        name = p.get('name', 'Brak nazwy')
        p_id = p.get('id', 'Brak')
        price = p.get('price', 0)
        old_price = p.get('oldPrice')
        badge = p.get('badge')
        p_type = p.get('type', 'Inne')
        smaki = p.get('smaki', [])
        
        price_str = f"~~{old_price} PLN~~ ➔ **{price} PLN**" if old_price else f"**{price} PLN**"
        badge_str = f" [{badge}]" if badge else ""
        smaki_str = ", ".join(smaki) if smaki else "Brak"

        embed.add_field(
            name=f"{name}{badge_str}",
            value=f"• **Typ:** `{p_type}`\n• **Cena:** {price_str}\n• **Smaki ({len(smaki)}):** `{smaki_str}`\n• **ID:** `{p_id}`",
            inline=False
        )
    await interaction.followup.send(embed=embed)

@bot.tree.command(name="dodaj", description="Dodaje nowy produkt do sklepu na GitHubie")
@app_commands.describe(nazwa="Nazwa produktu", cena="Cena w PLN", typ="Typ: np. snus lub Inne", smaki="Smaki oddzielone przecinkiem")
@app_commands.default_permissions(administrator=True)
async def dodaj(interaction: discord.Interaction, nazwa: str, cena: float, typ: str = "Inne", stara_cena: float = None, badge: str = None, smaki: str = "Watermelon Ice", img: str = "", product_id: str = None):
    await interaction.response.defer(ephemeral=True)
    products, _, _ = get_github_file()
    if not isinstance(products, list):
        products = []
        
    if not product_id:
        product_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
        
    smaki_list = [s.strip() for s in smaki.split(",") if s.strip()]
    new_product = {
        "id": product_id, "type": typ.lower(), "name": nazwa, "price": cena,
        "oldPrice": stara_cena, "badge": badge, "img": img, "smaki": smaki_list
    }
    
    products.append(new_product)
    if update_github_file(products, f"Dodano produkt {nazwa}"):
        await interaction.followup.send(f"✅ Dodano produkt `{nazwa}` (ID: `{product_id}`)", ephemeral=True)
    else:
        await interaction.followup.send("❌ Błąd zapisu na GitHubie.", ephemeral=True)

@bot.tree.command(name="promo", description="Tworzy lub aktualizuje kod rabatowy")
@app_commands.default_permissions(administrator=True)
async def promo(interaction: discord.Interaction, kod: str, procent: float):
    await interaction.response.defer(ephemeral=True)
    code_upper = kod.strip().upper()
    promos, _, _ = get_github_promos()
    if not isinstance(promos, dict):
        promos = {}
    promos[code_upper] = procent
    
    if update_github_promos(promos, f"Kod {code_upper}"):
        await interaction.followup.send(f"✅ Kod `{code_upper}` na `{procent}%` zapisany!", ephemeral=True)
    else:
        await interaction.followup.send("❌ Błąd zapisu kodu.", ephemeral=True)

@bot.tree.command(name="status_paczki", description="[Admin] Aktualizuje status przesyłki")
@app_commands.default_permissions(administrator=True)
async def status_paczki(interaction: discord.Interaction, order_id: str, status_opisu: str):
    await interaction.response.defer(ephemeral=True)
    oid = order_id.strip().upper()
    tracking_data, _, _ = get_github_tracking()
    if not isinstance(tracking_data, dict):
        tracking_data = {}
    if oid not in tracking_data:
        tracking_data[oid] = {}
    tracking_data[oid]["status"] = status_opisu
    
    if update_github_tracking(tracking_data, f"Status {oid}"):
        await interaction.followup.send(f"✅ Zaktualizowano status dla `{oid}`", ephemeral=True)
    else:
        await interaction.followup.send("❌ Błąd zapisu.", ephemeral=True)

@bot.tree.command(name="sprawdz_paczke", description="Sprawdza status przesyłki")
async def sprawdz_paczke(interaction: discord.Interaction, order_id: str):
    await interaction.response.defer(ephemeral=True)
    oid = order_id.strip().upper()
    tracking_data, _, _ = get_github_tracking()
    if not isinstance(tracking_data, dict) or oid not in tracking_data:
        await interaction.followup.send(f"❌ Brak przesyłki o ID `{oid}`", ephemeral=True)
        return
    current_status = tracking_data[oid].get("status", "Brak")
    await interaction.followup.send(f"📦 Status dla `{oid}`: **{current_status}**", ephemeral=True)

@bot.tree.command(name="start_ocen", description="Wysyła panel opinii")
@app_commands.default_permissions(administrator=True)
async def start_ocen(interaction: discord.Interaction):
    embed = discord.Embed(title="⭐ Oceń zakupy w naszym sklepie!", description="Kliknij poniższy przycisk:", color=discord.Color.blurple())
    await interaction.channel.send(embed=embed, view=ReviewButtonView())
    await interaction.response.send_message("✅ Panel wysłany!", ephemeral=True)

@bot.tree.command(name="zamowienie", description="[Ręczne] Otwórz ticket dla zamówienia")
async def zamowienie(interaction: discord.Interaction, order_id: str):
    await interaction.response.defer(ephemeral=True)
    orders, _, _ = get_github_orders()
    order = next((o for o in orders if str(o.get('id')).upper() == order_id.upper()), None)
    if not order:
        await interaction.followup.send(f"❌ Nie znaleziono zamówienia `{order_id}`", ephemeral=True)
        return

    guild = interaction.guild
    channel_name = f"zamowienie-{order_id}".lower()
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
    }
    admin_roles = [r for r in guild.roles if r.permissions.administrator and r != guild.default_role]
    for r in admin_roles:
        overwrites[r] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

    ticket_channel = await guild.create_text_channel(name=channel_name, overwrites=overwrites)
    await interaction.followup.send(f"✅ Utworzono ticket: {ticket_channel.mention}", ephemeral=True)
    
    embed = discord.Embed(title=f"🛒 Zamówienie {order_id}", color=discord.Color.green())
    embed.add_field(name="Klient", value=order.get('discord'), inline=True)
    embed.add_field(name="Suma", value=f"{order.get('total')} PLN", inline=True)
    await ticket_channel.send(embed=embed)

@bot.tree.command(name="zamknij", description="Zamyka ticket")
async def zamknij(interaction: discord.Interaction):
    if "zamowienie-" in interaction.channel.name:
        await interaction.response.send_message("🔒 Zamykanie...")
        await asyncio.sleep(2)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("❌ Komenda tylko na kanale zamówienia.", ephemeral=True)

@bot.tree.command(name="usundowody", description="[Awaryjne] Czyszczenie danych")
@app_commands.default_permissions(administrator=True)
async def usundowody(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    update_github_file([], "Wipe")
    update_github_orders([], "Wipe")
    update_github_promos({}, "Wipe")
    update_github_reviews([], "Wipe")
    update_github_tracking({}, "Wipe")
    update_github_users([], "Wipe")
    await interaction.followup.send("🚨 Wyczyszczono dane na GitHubie!", ephemeral=True)

@bot.tree.command(name="rr", description="Restart bota")
@app_commands.default_permissions(administrator=True)
async def rr(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 Restart...", ephemeral=True)
    os._exit(0)

def run_flask():
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)

if __name__ == "__main__":
    # Uruchomienie Flaska w osobnym wątku
    threading.Thread(target=run_flask, daemon=True).start()
    # Uruchomienie bota Discord w głównym wątku (wymagane dla poprawnej pracy biblioteki discord.py)
    bot.run(DISCORD_TOKEN)

