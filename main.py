import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import os
import asyncio

# --- SEKCA KEEP ALIVE (DLA RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Mint.mc Bot is Online!"

def run():
    # Render wymaga portu ze zmiennej środowiskowej
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KONFIGURACJA BOTA ---
TOKEN = "MTUwNDkyNDY0MTQxMDY4Mjk1MA.GtOXeL.hFpSnpa_jhBtjBEc-0YaTColiV5iKD5YjEpUK8"

class MintBot(commands.Bot):
    def __init__(self):
        # Wymagane Intents dla poprawnego działania
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Komendy slash zsynchronizowane!")

bot = MintBot()

@bot.event
async def on_ready():
    print(f"🚀 Bot gotowy! Zalogowano jako {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="/setup | Mint.mc"))

# --- KOMENDA SETUP (MAKSYMALNA ILOŚĆ KANAŁÓW) ---
@bot.tree.command(name="setup", description="Buduje potężny serwer Mint.mc ze wszystkimi kanałami")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. TWORZENIE RANG
    roles_data = {
        "👑 CEO": discord.Color.red(),
        "💻 DEV": discord.Color.purple(),
        "🛠️ ADMIN": discord.Color.orange(),
        "🛡️ MOD": discord.Color.blue(),
        "🟢 GRACZ": discord.Color.green()
    }
    
    created_roles = {}
    for name, color in roles_data.items():
        role = discord.utils.get(guild.roles, name=name)
        if not role:
            role = await guild.create_role(name=name, color=color, hoist=True)
        created_roles[name] = role

    everyone = guild.default_role

    # 2. STRUKTURA KANAŁÓW

    # --- REGULAMIN ---
    cat_reg = await guild.create_category("MINT.MC - REGULAMIN")
    await guild.create_text_channel("📋┃regulamin", category=cat_reg)
    await guild.create_text_channel("📜┃zakazane-mody", category=cat_reg)
    await guild.create_text_channel("👮┃taryfikator", category=cat_reg)

    # --- LOBBY ---
    cat_lobby = await guild.create_category("MINT.MC - LOBBY")
    await guild.create_text_channel("💜┃boosty", category=cat_lobby)
    await guild.create_text_channel("👑┃rangi", category=cat_lobby)
    await guild.create_text_channel("🔧┃role", category=cat_lobby)
    await guild.create_text_channel("👋┃powitania", category=cat_lobby)

    # --- HOSTING ---
    cat_host = await guild.create_category("MINT.MC - HOSTING")
    await guild.create_text_channel("❗┃cytrushost", category=cat_host)

    # --- INFORMACJE ---
    cat_info = await guild.create_category("MINT.MC - INFORMACJE")
    await guild.create_text_channel("📌┃ogloszenia", category=cat_info)
    await guild.create_text_channel("🚧┃changelog", category=cat_info)
    await guild.create_text_channel("⚙️┃rekrutacja", category=cat_info)
    await guild.create_text_channel("📊┃ankiety", category=cat_info)
    await guild.create_text_channel("🎁┃konkursy", category=cat_info)
    await guild.create_text_channel("🎉┃eventy", category=cat_info)
    await guild.create_text_channel("💎┃partnerstwa", category=cat_info)

    # --- POMOC (W tym kanały głosowe) ---
    cat_help = await guild.create_category("MINT.MC - POMOC")
    await guild.create_text_channel("📝┃stworz-ticket", category=cat_help)
    await guild.create_text_channel("📑┃zasady-ticketow", category=cat_help)
    await guild.create_voice_channel("❓ ‧ POMOC", category=cat_help)
    await guild.create_voice_channel("🚨 ‧ SPRAWDZANIE", category=cat_help)
    await guild.create_voice_channel("⚠️ ‧ WYTŁUMACZENIE", category=cat_help)

    # --- MEDIA ---
    cat_media = await guild.create_category("MINT.MC - MEDIA")
    await guild.create_text_channel("🚨┃content", category=cat_media)
    await guild.create_text_channel("🎥┃content-media", category=cat_media)
    await guild.create_text_channel("📸┃zrzuty-ekranu", category=cat_media)

    # --- STREFA GRACZA ---
    cat_player = await guild.create_category("MINT.MC - STREFA GRACZA")
    await guild.create_text_channel("💬┃chat-glowny", category=cat_player)
    await guild.create_text_channel("⛏️┃pochwal-sie", category=cat_player)
    await guild.create_text_channel("🤖┃komendy-botow", category=cat_player)
    await guild.create_voice_channel("🔊 ‧ POCZEKALNIA", category=cat_player)
    await guild.create_voice_channel("🎮 ‧ GRAMY #1", category=cat_player)
    await guild.create_voice_channel("🎮 ‧ GRAMY #2", category=cat_player)

    # 3. UPRAWNIENIA
    # Ukrywamy wszystko przed niezweryfikowanymi
    for category in [cat_lobby, cat_host, cat_info, cat_help, cat_media, cat_player]:
        await category.set_permissions(everyone, read_messages=False)
        await category.set_permissions(created_roles["🟢 GRACZ"], read_messages=True)

    await interaction.followup.send("✅ Serwer Mint.mc został w pełni zbudowany! Sprawdź kanały.", ephemeral=True)

# --- KOMENDA SPRAWDZANIA ---
@bot.tree.command(name="sprawdz", description="Przenosi gracza do izolatki na sprawdzanie")
@app_commands.checks.has_permissions(move_members=True)
async def sprawdz(interaction: discord.Interaction, gracz: discord.Member):
    voice_target = discord.utils.get(interaction.guild.voice_channels, name="🚨 ‧ SPRAWDZANIE")
    
    if gracz.voice:
        await gracz.move_to(voice_target)
        await interaction.response.send_message(f"🚨 Przeniesiono {gracz.mention} do kanału sprawdzania!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {gracz.mention} nie jest na głosowym. Musi tam wejść!", ephemeral=True)

# --- URUCHOMIENIE ---
if __name__ == "__main__":
    keep_alive() # Zapobiega uśpieniu na Render
    bot.run(TOKEN)
