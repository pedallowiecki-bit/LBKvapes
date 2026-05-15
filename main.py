import discord
from discord import app_commands
from discord.ext import commands

# TWÓJ TOKEN
TOKEN = "MTUwNDkyNDY0MTQxMDY4Mjk1MA.GtOXeL.hFpSnpa_jhBtjBEc-0YaTColiV5iKD5YjEpUK8"

class MintBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.all()
        super().__init__(command_prefix="!", intents=intents)

    async def setup_hook(self):
        # Synchronizacja komend / z serwerami
        await self.tree.sync()
        print("✅ Komendy slash (/) zostały zsynchronizowane!")

bot = MintBot()

@bot.event
async def on_ready():
    print(f"✅ Bot {bot.user.name} jest online (Slash Commands Mode)")
    await bot.change_presence(activity=discord.Activity(type=discord.ActivityType.watching, name="Mint.mc"))

# ==========================================
# 🏗️ KOMENDA /SETUP
# ==========================================
@bot.tree.command(name="setup", description="Buduje serwer Mint.mc w stylu Mooneu")
@app_commands.checks.has_permissions(administrator=True)
async def setup(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    guild = interaction.guild

    # --- TWORZENIE RANG ---
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

    # --- KATEGORIE I KANAŁY (Styl Mooneu) ---

    # 1. REGULAMIN
    cat_reg = await guild.create_category("MINT.MC - REGULAMIN")
    await guild.create_text_channel("📋┃regulamin", category=cat_reg)
    await guild.create_text_channel("📜┃zakazane-mody", category=cat_reg)
    await guild.create_text_channel("👮┃taryfikator", category=cat_reg)

    # 2. LOBBY
    cat_lobby = await guild.create_category("MINT.MC - LOBBY")
    await guild.create_text_channel("💜┃boosty", category=cat_lobby)
    await guild.create_text_channel("👑┃rangi", category=cat_lobby)
    await guild.create_text_channel("🔧┃role", category=cat_lobby)

    # 3. INFORMACJE
    cat_info = await guild.create_category("MINT.MC - INFORMACJE")
    await guild.create_text_channel("📌┃ogloszenia", category=cat_info)
    await guild.create_text_channel("🚧┃changelog", category=cat_info)
    await guild.create_text_channel("⚙️┃rekrutacja", category=cat_info)
    await guild.create_text_channel("📊┃ankiety", category=cat_info)

    # 4. POMOC
    cat_help = await guild.create_category("MINT.MC - POMOC")
    await guild.create_text_channel("📝┃stworz-ticket", category=cat_help)
    await guild.create_text_channel("📑┃zasady-ticketów", category=cat_help)
    ch_help_v = await guild.create_voice_channel("❓ ‧ POMOC", category=cat_help)
    ch_check_v = await guild.create_voice_channel("🚨 ‧ SPRAWDZANIE", category=cat_help)

    # 5. MEDIA
    cat_media = await guild.create_category("MINT.MC - MEDIA")
    await guild.create_text_channel("🚨┃content", category=cat_media)
    await guild.create_text_channel("🎥┃content-media", category=cat_media)

    # --- PERMISJE ---
    for category in [cat_lobby, cat_info, cat_help, cat_media]:
        await category.set_permissions(everyone, read_messages=False)
        await category.set_permissions(created_roles["🟢 GRACZ"], read_messages=True)

    await interaction.followup.send("✅ Serwer został zbudowany zgodnie ze wzorem!", ephemeral=True)

# ==========================================
# 🚨 KOMENDA /SPRAWDZ
# ==========================================
@bot.tree.command(name="sprawdz", description="Przenosi gracza na kanał sprawdzania")
@app_commands.describe(użytkownik="Gracz, którego chcesz sprawdzić")
@app_commands.checks.has_permissions(move_members=True)
async def sprawdz(interaction: discord.Interaction, użytkownik: discord.Member):
    voice_target = discord.utils.get(interaction.guild.voice_channels, name="🚨 ‧ SPRAWDZANIE")
    
    if użytkownik.voice:
        await użytkownik.move_to(voice_target)
        await interaction.response.send_message(f"🚨 Przeniesiono {użytkownik.mention} do izolatki!", ephemeral=True)
    else:
        await interaction.response.send_message(f"❌ {użytkownik.mention} nie jest na żadnym kanale głosowym.", ephemeral=True)

# ==========================================
# ✅ KOMENDA /WERYFIKACJA
# ==========================================
@bot.tree.command(name="weryfikacja", description="Nadaje rangę gracza")
async def weryfikacja(interaction: discord.Interaction):
    role = discord.utils.get(interaction.guild.roles, name="🟢 GRACZ")
    if role in interaction.user.roles:
        await interaction.response.send_message("Już jesteś zweryfikowany!", ephemeral=True)
    else:
        await interaction.user.add_roles(role)
        await interaction.response.send_message("🎉 Zostałeś zweryfikowany na Mint.mc!", ephemeral=True)

bot.run(TOKEN)