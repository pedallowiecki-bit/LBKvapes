import discord
from discord import app_commands
from discord.ext import commands
import os
import time
import hashlib
from flask import Flask
from threading import Thread

# --- KONFIGURACJA ---
TOKEN = "MTUwNDkyNDY0MTQxMDY4Mjk1MA.GtOXeL.hFpSnpa_jhBtjBEc-0YaTColiV5iKD5YjEpUK8"
SALT = "TITAN_ULTIMATE_2026"

# --- SERWER WWW DLA RENDER (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Mint.mc & Titan Server is Running"
def run_web(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run_web).start()

# --- WIDOKI UI (TICKETY I WERYFIKACJA) ---
class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✅ Weryfikacja", style=discord.ButtonStyle.success, custom_id="ver_btn")
    async def verify(self, interaction: discord.Interaction):
        role = discord.utils.get(interaction.guild.roles, name="🟢 GRACZ")
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Nadano rangę Gracz!", ephemeral=True)

# --- BOT CLASS ---
class MintTitanBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        self.add_view(VerifyView())
        await self.tree.sync()
        print("✅ Komendy slash zsynchronizowane!")

bot = MintTitanBot()

@bot.event
async def on_ready():
    print(f"🚀 Zalogowano jako {bot.user.name}")

# --- GENERATOR KLUCZA ---
def generate_titan_key():
    time_window = int(time.time() / 20)
    raw_string = str(time_window) + SALT
    md5_hash = hashlib.md5(raw_string.encode()).hexdigest().upper()
    return f"TITAN-{md5_hash[:8]}"

# --- KOMENDA SETUP (RANGI + MASA KANAŁÓW) ---
@bot.tree.command(name="setup", description="Buduje serwer Mint.mc: Rangi i Masa kanałów")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # 1. RANGI
    roles_data = {
        "👑 CEO": discord.Color.red(),
        "💻 DEV": discord.Color.purple(),
        "🛠️ ADMIN": discord.Color.orange(),
        "🛡️ MOD": discord.Color.blue(),
        "🟢 GRACZ": discord.Color.green()
    }
    for name, color in roles_data.items():
        if not discord.utils.get(guild.roles, name=name):
            await guild.create_role(name=name, color=color, hoist=True)

    # 2. STRUKTURA KANAŁÓW (Masa Chatów)
    structure = {
        "MINT.MC - INFORMACJE": ["📋┃regulamin", "📜┃zakazane-mody", "📌┃ogloszenia", "🚧┃changelog", "🎁┃konkursy"],
        "MINT.MC - LOBBY": ["💜┃boosty", "👑┃rangi", "👋┃powitania", "🛡️┃weryfikacja"],
        "MINT.MC - STREFA CHATU": [
            "💬┃chat-ogolny", "💬┃chat-2", "💬┃chat-vip", "⛏️┃zrzuty-z-gry", 
            "🤖┃komendy-botow", "🎭┃memy", "🎨┃tworczosc", "🍱┃jedzenie", 
            "🚗┃motoryzacja", "🎮┃szukam-ekipy", "🍕┃lifestyle", "🎞️┃filmy"
        ],
        "MINT.MC - MEDIA": ["🚨┃content", "🎥┃content-media", "📸┃galeria"],
        "MINT.MC - POMOC": ["📝┃stworz-ticket", "📑┃zasady-ticketow", "🚨┃sprawdzanie"]
    }

    for cat_name, channels in structure.items():
        category = await guild.create_category(cat_name)
        for ch_name in channels:
            chan = await guild.create_text_channel(ch_name, category=category)
            if "weryfikacja" in ch_name:
                await chan.send("🛡️ **KLIKNIJ PRZYCISK, ABY DOSTAĆ SIĘ NA SERWER**", view=VerifyView())

    await interaction.followup.send("🔥 Serwer Mint.mc został rozbudowany!", ephemeral=True)

# --- KOMENDA GEN ---
@bot.tree.command(name="gen", description="Generuje klucz TITAN")
async def gen(interaction: discord.Interaction):
    key = generate_titan_key()
    await interaction.response.send_message(f"🔑 Twój klucz: `{key}` (Ważny 20s)", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
