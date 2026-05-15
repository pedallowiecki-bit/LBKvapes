import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# --- SERWER WWW DLA RENDER (KEEP ALIVE) ---
app = Flask('')

@app.route('/')
def home():
    return "Mint.mc Status: ONLINE"

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
    print(f"🚀 Bot Mint.mc jest AKTYWNY jako {bot.user.name}")
    await bot.change_presence(activity=discord.Game(name="Mint.mc | /setup"))

# --- MEGA SETUP: RANGI + MASA CHATÓW ---
@bot.tree.command(name="setup", description="Pełna konfiguracja: Rangi i wszystkie kanały")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. TWORZENIE RANG
    roles_data = {
        "👑 CEO": discord.Color.red(),
        "🛠️ ADMIN": discord.Color.orange(),
        "🛡️ MOD": discord.Color.blue(),
        "🛡️ HELPER": discord.Color.dark_blue(),
        "💎 VIP": discord.Color.gold(),
        "🟢 GRACZ": discord.Color.green()
    }
    
    created_roles = {}
    for name, color in roles_data.items():
        role = discord.utils.get(guild.roles, name=name)
        if not role:
            role = await guild.create_role(name=name, color=color, hoist=True)
        created_roles[name] = role

    # 2. ROZBUDOWANA LISTA KANAŁÓW (Masa Chatów)
    structure = {
        "MINT.MC - INFORMACJE": ["📋┃regulamin", "📜┃zakazane-mody", "👮┃taryfikator", "📌┃ogloszenia", "🚧┃changelog"],
        "MINT.MC - LOBBY": ["💜┃boosty", "👑┃rangi", "🔧┃role", "👋┃powitania"],
        "MINT.MC - STREFA CHATU": [
            "💬┃chat-ogolny", "💬┃chat-2", "💬┃chat-vip", "⛏️┃zrzuty-z-gry", 
            "🤖┃komendy-botow", "🎭┃memy", "🎨┃tworczosc", "🍱┃jedzenie", 
            "🚗┃motoryzacja", "🎮┃szukam-ekipy", "🍕┃lifestyle"
        ],
        "MINT.MC - MEDIA": ["🚨┃content", "🎥┃content-media", "📸┃galeria"],
        "MINT.MC - POMOC": ["📝┃stworz-ticket", "📑┃zasady-ticketow", "🛡️┃zgloszenia"],
    }

    for cat_name, channels in structure.items():
        category = await guild.create_category(cat_name)
        for ch_name in channels:
            await guild.create_text_channel(ch_name, category=category)

    # 3. KANAŁY GŁOSOWE
    v_cat = await guild.create_category("MINT.MC - GŁOSOWE")
    v_channels = ["🔊┃Poczekalnia", "🔊┃Chat #1", "🔊┃Chat #2", "🎮┃Gramy #1", "🚨┃SPRAWDZANIE"]
    for v_name in v_channels:
        await guild.create_voice_channel(v_name, category=v_cat)

    await interaction.followup.send("🔥 Serwer Mint.mc zbudowany pomyślnie! Rangi i kanały gotowe.", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
