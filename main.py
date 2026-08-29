import os
import json
import base64
import requests
import discord
from discord import app_commands
from discord.ext import commands

# Zmienne środowiskowe z panelu Render
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
GITHUB_REPO = os.getenv("GITHUB_REPO")

FILE_PATH = "products.json"
GITHUB_API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/contents/{FILE_PATH}"

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

def get_github_file():
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    res = requests.get(GITHUB_API_URL, headers=headers)
    if res.status_code == 200:
        data = res.json()
        content = requests.get(data['download_url']).text
        return json.loads(content), data['sha']
    return [], None

def update_github_file(products, sha, commit_message):
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    content_json = json.dumps(products, indent=2, ensure_ascii=False)
    encoded_content = base64.b64encode(content_json.encode('utf-8')).decode('utf-8')
    
    payload = {
        "message": commit_message,
        "content": encoded_content,
        "sha": sha
    }
    
    res = requests.put(GITHUB_API_URL, headers=headers, json=payload)
    return res.status_code in [200, 201]

@bot.event
async def on_ready():
    print(f"✅ Bot jest ONLINE jako: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"🔄 Zsynchronizowano {len(synced)} komend(y) slash!")
    except Exception as e:
        print(f"❌ Błąd synchronizacji komend: {e}")

# KOMENDA: /sklep
@bot.tree.command(name="sklep", description="Wyświetla aktualne produkty ze sklepu")
async def sklep(interaction: discord.Interaction):
    await interaction.response.defer()
    products, _ = get_github_file()
    
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
        embed.add_field(
            name=f"{badge}{p.get('name')}",
            value=f"Cena: {old_price}**{price} PLN**\nID: `{p.get('id')}`",
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

# KOMENDA: /dodaj
@bot.tree.command(name="dodaj", description="[ADMIN] Dodaj nowy produkt do sklepu")
@app_commands.checks.has_permissions(administrator=True)
async def dodaj(
    interaction: discord.Interaction, 
    nazwa: str, 
    cena: float, 
    stara_cena: float = None, 
    odznaka: str = None, 
    obrazek: str = None
):
    await interaction.response.defer(ephemeral=True)
    products, sha = get_github_file()
    
    if sha is None:
        await interaction.followup.send("❌ Nie można połączyć się z GitHubem. Sprawdź token i nazwę repozytorium w Renderze.")
        return

    new_product = {
        "id": int(discord.utils.utcnow().timestamp()),
        "name": nazwa,
        "price": cena,
        "oldPrice": stara_cena,
        "badge": odznaka,
        "img": obrazek or "https://via.placeholder.com/200"
    }

    products.append(new_product)
    
    if update_github_file(products, sha, f"Dodano produkt: {nazwa}"):
        await interaction.followup.send(f"✅ Pomyślnie dodano produkt **{nazwa}**!")
    else:
        await interaction.followup.send("❌ Błąd podczas zapisu na GitHubie.")

# KOMENDA: /usun
@bot.tree.command(name="usun", description="[ADMIN] Usuń produkt ze sklepu po ID")
@app_commands.checks.has_permissions(administrator=True)
async def usun(interaction: discord.Interaction, product_id: int):
    await interaction.response.defer(ephemeral=True)
    products, sha = get_github_file()
    
    if sha is None:
        await interaction.followup.send("❌ Nie można połączyć się z GitHubem.")
        return

    new_products = [p for p in products if p.get('id') != product_id]

    if len(products) == len(new_products):
        await interaction.followup.send(f"❌ Nie znaleziono produktu o ID `{product_id}`.")
        return

    if update_github_file(new_products, sha, f"Usunięto produkt ID: {product_id}"):
        await interaction.followup.send(f"✅ Usunięto produkt o ID `{product_id}`.")
    else:
        await interaction.followup.send("❌ Błąd podczas zapisu na GitHubie.")

# KOMENDA: /zamowienie
@bot.tree.command(name="zamowienie", description="Realizacja zamówienia ze strony WWW")
async def zamowienie(interaction: discord.Interaction, id: str):
    embed = discord.Embed(
        title="🛒 Otrzymano nowe zamówienie!",
        description=f"Klient {interaction.user.mention} przesłał kod zamówienia: **{id}**",
        color=discord.Color.green()
    )
    await interaction.response.send_message(embed=embed)

# Obsługa błędu braku uprawnień admina
@dodaj.error
@usun.error
async def admin_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.MissingPermissions):
        await interaction.response.send_message("❌ Musisz posiadać uprawnienie **Administrator** w roli na Discordzie, aby użyć tej komendy!", ephemeral=True)

bot.run(DISCORD_TOKEN)
