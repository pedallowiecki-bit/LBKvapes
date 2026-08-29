import os
import json
import base64
import requests
import threading
import asyncio
import sys
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord import app_commands
from discord.ext import commands

# --- SERWER UTRZYMUJĄCY BOTA AKTYWNEGO W RENDERZE ---
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Bot status: ONLINE")

    def log_message(self, format, *args):
        return

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(('0.0.0.0', port), SimpleHTTPRequestHandler)
    server.serve_forever()

threading.Thread(target=run_web_server, daemon=True).start()

# --- ZMIENNE ŚRODOWISKOWE ---
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

FILE_PATH = "products.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

intents = discord.Intents.default()
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

def get_headers():
    token = GITHUB_TOKEN.strip() if GITHUB_TOKEN else ""
    return {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "DiscordBot-LBK"
    }

def get_github_file():
    if not GITHUB_TOKEN or not GITHUB_REPO:
        return [], None, "Brak zmiennych GITHUB w Renderze!"

    try:
        res = requests.get(GITHUB_API_URL, headers=get_headers())
        if res.status_code == 200:
            data = res.json()
            download_url = data.get('download_url')
            file_res = requests.get(download_url, headers={"User-Agent": "DiscordBot-LBK"})
            return json.loads(file_res.text), data.get('sha'), None
        else:
            return [], None, f"GitHub API zwrócił błąd: {res.status_code}"
    except Exception as e:
        return [], None, f"Błąd połączenia: {str(e)}"

def update_github_file(products, sha, commit_message):
    content_json = json.dumps(products, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha
    }
    
    res = requests.put(GITHUB_API_URL, headers=get_headers(), json=payload)
    return res.status_code in [200, 201]

@bot.event
async def on_ready():
    print(f"✅ Bot jest ONLINE jako: {bot.user}")
    await bot.change_presence(
        status=discord.Status.online,
        activity=discord.Game(name="/sklep | LBKPETS")
    )
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Zsynchronizowano {len(synced)} komend!")
    except Exception as e:
        print(f"❌ Błąd synchronizacji: {e}")

# KOMENDA: /sklep
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

    embed = discord.Embed(
        title="🛍️ Oferta Sklepu LBKPETS",
        description="Oto lista dostępnych produktów:",
        color=discord.Color.blue()
    )
    
    for p in products:
        price = p.get('price', 0)
        old_price = f"~~{p.get('oldPrice')} PLN~~ " if p.get('oldPrice') else ""
        badge = f"[{p.get('badge')}] " if p.get('badge') else ""
        typ = f"Typ: {p.get('type')}\n" if p.get('type') else ""
        embed.add_field(
            name=f"{badge}{p.get('name')}",
            value=f"{typ}Cena: {old_price}**{price} PLN**\nID: `{p.get('id')}`",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

# KOMENDA: /dodaj
@bot.tree.command(name="dodaj", description="Dodaj nowy produkt do sklepu")
@app_commands.describe(
    id_produktu="Unikalne ID produktu (np. LBK-9LYGP ze strony)",
    typ="Wybierz typ produktu",
    nazwa="Nazwa produktu",
    cena="Cena produktu",
    stara_cena="Poprzednia cena (opcjonalnie)",
    odznaka="Tekst odznaki np. PROMOCJA (opcjonalnie)",
    obrazek="Link do obrazka (opcjonalnie)"
)
@app_commands.choices(typ=[
    app_commands.Choice(name="Box", value="Box"),
    app_commands.Choice(name="Inne", value="Inne")
])
@app_commands.default_permissions(administrator=True)
async def dodaj(
    interaction: discord.Interaction, 
    id_produktu: str,
    typ: app_commands.Choice[str],
    nazwa: str, 
    cena: float, 
    stara_cena: float = None, 
    odznaka: str = None, 
    obrazek: str = None
):
    await interaction.response.defer(ephemeral=True)
    products, sha, error = get_github_file()
    
    if error:
        await interaction.followup.send(f"❌ {error}")
        return

    new_product = {
        "id": id_produktu,
        "type": typ.value,
        "name": nazwa,
        "price": cena,
        "oldPrice": stara_cena,
        "badge": odznaka,
        "img": obrazek or "https://via.placeholder.com/200"
    }

    products.append(new_product)
    
    if update_github_file(products, sha, f"Dodano produkt ({typ.value}): {nazwa}"):
        await interaction.followup.send(f"✅ Pomyślnie dodano produkt **{nazwa}** z ID `{id_produktu}`!")
    else:
        await interaction.followup.send("❌ Błąd zapisu na GitHubie (sprawdź token).")

# KOMENDA: /usun
@bot.tree.command(name="usun", description="Usuń produkt ze sklepu po ID")
@app_commands.describe(product_id="ID produktu (np. LBK-9LYGP)")
@app_commands.default_permissions(administrator=True)
async def usun(interaction: discord.Interaction, product_id: str):
    await interaction.response.defer(ephemeral=True)
    products, sha, error = get_github_file()
    
    if error:
        await interaction.followup.send(f"❌ {error}")
        return

    new_products = [p for p in products if str(p.get('id')) != product_id]

    if len(products) == len(new_products):
        await interaction.followup.send(f"❌ Nie znaleziono produktu o ID `{product_id}`.")
        return

    if update_github_file(new_products, sha, f"Usunięto produkt ID: {product_id}"):
        await interaction.followup.send(f"✅ Usunięto produkt o ID `{product_id}`.")
    else:
        await interaction.followup.send("❌ Błąd zapisu na GitHubie.")

# KOMENDA: /zamowienie (OBSŁUGUJE TEKSTOWE ID ZE STRONY, NP. LBK-9LYGP)
@bot.tree.command(name="zamowienie", description="Otwórz ticket w celu zakupu produktu ze sklepu")
@app_commands.describe(product_id="ID produktu (np. LBK-9LYGP skopiowane ze strony)")
async def zamowienie(interaction: discord.Interaction, product_id: str):
    await interaction.response.defer(ephemeral=True)

    products, _, error = get_github_file()
    if error:
        await interaction.followup.send(f"❌ Błąd wczytywania sklepu: {error}", ephemeral=True)
        return

    product = next((p for p in products if str(p.get('id')) == product_id), None)
    if not product:
        await interaction.followup.send(f"❌ Nie znaleziono produktu o ID `{product_id}`. Sprawdź poprawność kodu ze strony.", ephemeral=True)
        return

    guild = interaction.guild
    user = interaction.user

    if not guild:
        await interaction.followup.send("❌ Tej komendy można używać tylko na serwerze.", ephemeral=True)
        return

    try:
        nazwa = product.get('name', 'Produkt')
        cena = float(product.get('price', 0))
        obrazek = product.get('img', '')
        dostawa = 15.0
        suma = cena + dostawa

        raw_overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            user: discord.PermissionOverwrite(read_messages=True, send_messages=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }

        overwrites = {
            target: perm for target, perm in raw_overwrites.items() 
            if target is not None and hasattr(target, 'id')
        }

        channel_name = f"ticket-{user.name}".lower().replace(" ", "-")
        
        ticket_channel = await guild.create_text_channel(
            name=channel_name,
            overwrites=overwrites
        )

        await interaction.followup.send(
            f"✅ **Otworzono prywatny ticket!** Przejdź na kanał: {ticket_channel.mention}", 
            ephemeral=True
        )

        embed = discord.Embed(
            title="🛒 Nowe Zamówienie / Ticket",
            description=f"Witaj {user.mention}!\nOtworzyliśmy Twój prywatny ticket dotyczący zakupu w sklepie **LBKPETS**.",
            color=discord.Color.green()
        )
        embed.add_field(name="👤 Klient", value=user.mention, inline=True)
        embed.add_field(name="📦 Zamówienie", value=f"**{nazwa}** (ID: `{product_id}`)", inline=False)
        embed.add_field(name="💵 Cena produktu", value=f"{cena:.2f} PLN", inline=True)
        embed.add_field(name="🚚 Dostawa", value=f"{dostawa:.2f} PLN", inline=True)
        embed.add_field(name="💰 Łączna kwota", value=f"**{suma:.2f} PLN**", inline=False)

        if obrazek:
            embed.set_image(url=obrazek)

        embed.add_field(
            name="📌 Instrukcja", 
            value="1. Podaj metodę płatności (**BLIK / PSC / Crypto / Przelew**).\n2. Poczekaj na administrację.", 
            inline=False
        )
        embed.set_footer(text="LBKPETS • System Zamówień")

        await ticket_channel.send(content=f"{user.mention} | Powiadomiono Administrację", embed=embed)

    except Exception as e:
        await interaction.followup.send(f"❌ Wystąpił błąd podczas tworzenia ticketu: {e}", ephemeral=True)

# AUTOCOMPLETE DLA KOMENDY /zamowienie
@zamowienie.autocomplete('product_id')
async def zamowienie_autocomplete(interaction: discord.Interaction, current: str):
    products, _, _ = get_github_file()
    choices = []
    for p in products:
        name = p.get('name', 'Brak nazwy')
        price = p.get('price', 0)
        product_id = str(p.get('id', ''))
        
        if current.lower() in name.lower() or current.lower() in product_id.lower():
            choices.append(
                app_commands.Choice(name=f"{name} ({price} PLN) [ID: {product_id}]", value=product_id)
            )
    return choices[:25]

# KOMENDA: /zamknij
@bot.tree.command(name="zamknij", description="Zamyka i usuwa bieżący ticket")
async def zamknij(interaction: discord.Interaction):
    if "ticket-" in interaction.channel.name:
        await interaction.response.send_message("🔒 **Zamykanie ticketu za 5 sekund...**")
        await asyncio.sleep(5)
        await interaction.channel.delete()
    else:
        await interaction.response.send_message("❌ Tej komendy możesz użyć tylko na kanale ticketu.", ephemeral=True)

# KOMENDA: /restart
@bot.tree.command(name="restart", description="Restartuje bota")
@app_commands.default_permissions(administrator=True)
async def restart(interaction: discord.Interaction):
    await interaction.response.send_message("🔄 **Restartowanie bota...**", ephemeral=True)
    os.execv(sys.executable, ['python'] + sys.argv)

if __name__ == "__main__":
    if DISCORD_TOKEN:
        bot.run(DISCORD_TOKEN)
    else:
        print("❌ Brak zmiennej DISCORD_TOKEN!")
