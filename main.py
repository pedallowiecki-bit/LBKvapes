import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# --- SEKCA KEEP ALIVE (DLA RENDER) ---
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
    await bot.change_presence(activity=discord.Game(name="/setup | Mint.mc"))

# --- GŁÓWNA KOMENDA SETUP (RANGI + KANAŁY) ---
@bot.tree.command(name="setup", description="Buduje serwer Mint.mc (Rangi + Masa kanałów)")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. TWORZENIE RANG
    await interaction.followup.send("⏳ Tworzę rangi...", ephemeral=True)
    roles_to_create = {
        "👑 CEO": discord.Color.red(),
        "💻 DEV": discord.Color.purple(),
        "🛠️ ADMIN": discord.Color.orange(),
        "🛡️ MOD": discord.Color.blue(),
        "🛡️ HELPER": discord.Color.dark_blue(),
        "💎 VIP": discord.Color.gold(),
        "🟢 GRACZ": discord.Color.green()
    }

    created_roles = {}
    for r_name, r_color in roles_to_create.items():
        role = discord.utils.get(guild.roles, name=r_name)
        if not role:
            role = await guild.create_role(name=r_name, color=r_color, hoist=True)
        created_roles[r_name] = role

    # 2. TWORZENIE STRUKTURY KANAŁÓW
    await interaction.followup.send("⏳ Tworzę kategorie i kanały...", ephemeral=True)
    
    structure = {
        "MINT.MC - REGULAMIN": ["📋┃regulamin", "📜┃zakazane-mody", "👮┃taryfikator"],
        "MINT.MC - LOBBY": ["💜┃boosty", "👑┃rangi", "🔧┃role", "👋┃powitania"],
        "MINT.MC - INFORMACJE": ["📌┃ogloszenia", "🚧┃changelog", "⚙️┃rekrutacja", "📊┃ankiety", "🎁┃konkursy"],
        "MINT.MC - STREFA CHATU": [
            "💬┃chat-ogolny", "💬┃chat-2", "💬┃wolne-pisanie", 
            "⛏️┃zrzuty-z-gry", "🤖┃komendy-botow", "🎭┃memy", 
            "🎮┃szukam-ekipy", "🍕┃lifestyle", "🎞️┃filmy-i-seriale",
            "🎨┃tworczosc-graczy", "🍱┃jedzenie", "🚗┃motoryzacja"
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
    voice_channels = ["🔊┃Poczekalnia", "🔊┃Chat Głosowy #1", "🔊┃Chat Głosowy #2", "🎮┃Gramy #1", "🎮┃Gramy #2", "🚨┃SPRAWDZANIE"]
    for v_name in voice_channels:
        await guild.create_voice_channel(v_name, category=v_cat)

    await interaction.followup.send("✅ Serwer Mint.mc został w pełni skonfigurowany!", ephemeral=True)

# --- START ---
if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
