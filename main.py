import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# --- SEKCA KEEP ALIVE (WYMAGANE PRZEZ RENDER) ---
app = Flask('')

@app.route('/')
def home():
    return "Mint.mc Bot is Online!"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    t = Thread(target=run)
    t.start()

# --- KONFIGURACJA BOTA ---
TOKEN = "MTUwNDkyNDY0MTQxMDY4Mjk1MA.GtOXeL.hFpSnpa_jhBtjBEc-0YaTColiV5iKD5YjEpUK8"

class MintBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        await self.tree.sync()
        print("✅ Komendy slash zsynchronizowane!")

bot = MintBot()

@bot.event
async def on_ready():
    print(f"🚀 Zalogowano jako {bot.user.name}")

# --- MEGA ROZBUDOWANA KOMENDA SETUP ---
@bot.tree.command(name="setup", description="Buduje potężny serwer z masą kanałów")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # DEFINICJA KATEGORII I KANAŁÓW (Wszystko ze zdjęć + Twoja prośba)
    structure = {
        "MINT.MC - REGULAMIN": ["📋┃regulamin", "📜┃zakazane-mody", "👮┃taryfikator"],
        "MINT.MC - LOBBY": ["💜┃boosty", "👑┃rangi", "🔧┃role", "👋┃powitania", "📊┃statystyki"],
        "MINT.MC - HOSTING": ["❗┃cytrushost"],
        "MINT.MC - INFORMACJE": ["📌┃ogloszenia", "🚧┃changelog", "⚙️┃rekrutacja", "🌈┃partnerstwa", "📊┃ankiety", "🎁┃konkursy", "🎉┃eventy"],
        "MINT.MC - POMOC": ["📝┃stworz-ticket", "📑┃zasady-ticketow", "🛡️┃zglos-gracza", "❓┃pytania"],
        "MINT.MC - MEDIA": ["🚨┃content", "🎥┃content-media", "📸┃zrzuty-ekranu", "📽️┃tiktok-yt"],
        "MINT.MC - STREFA CHATU": ["💬┃chat-ogolny", "⛏️┃screeny-z-gry", "🤖┃boty", "🎭┃memowy", "🎮┃szukam-ekipy", "🎶┃muzyka"],
        "MINT.MC - EKONOMIA": ["💰┃portfel", "🛒┃sklep-serwerowy", "📈┃rankingi"]
    }

    for cat_name, channels in structure.items():
        category = await guild.create_category(cat_name)
        for ch_name in channels:
            await guild.create_text_channel(ch_name, category=category)

    # DODANIE KANAŁÓW GŁOSOWYCH
    voice_cat = await guild.create_category("MINT.MC - KANAŁY GŁOSOWE")
    await guild.create_voice_channel("🔊┃Poczekalnia", category=voice_cat)
    await guild.create_voice_channel("🎮┃Gramy #1", category=voice_cat)
    await guild.create_voice_channel("🎮┃Gramy #2", category=voice_cat)
    await guild.create_voice_channel("🚨┃SPRAWDZANIE", category=voice_cat)

    await interaction.followup.send("🔥 Serwer został rozbudowany! Sprawdź listę kanałów.", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
