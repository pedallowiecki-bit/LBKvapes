import discord
from discord import app_commands
from discord.ext import commands
from flask import Flask
from threading import Thread
import os

# --- TWOJE ID (ZWERYFIKOWANE) ---
TOKEN = "MTUwNDkyNDY0MTQxMDY4Mjk1MA.GtOXeL.hFpSnpa_jhBtjBEc-0YaTColiV5iKD5YjEpUK8"
VERIFY_ROLE_ID = 1504942313724448889  # ID rangi Gracz
WELCOME_CHANNEL_ID = 1504942324470251610 # ID kanału Powitania
TICKET_CATEGORY_ID = 1504942324470251610 # Kategoria dla ticketów

# --- SERWER WWW DLA RENDER (Keep Alive) ---
app = Flask('')
@app.route('/')
def home(): return "Mint.mc is Online!"
def run(): app.run(host='0.0.0.0', port=8080)
def keep_alive(): Thread(target=run).start()

# --- SYSTEM TICKETÓW (PRZYCISKI) ---
class TicketTypeView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def create_ticket(self, interaction: discord.Interaction, label: str):
        guild = interaction.guild
        category = guild.get_channel(TICKET_CATEGORY_ID)
        
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        
        channel = await guild.create_text_channel(
            name=f"{label}-{interaction.user.name}",
            category=category,
            overwrites=overwrites
        )
        
        embed = discord.Embed(title=f"Ticket: {label.upper()}", color=discord.Color.green())
        embed.description = f"Witaj {interaction.user.mention}, opisz swój problem. Administracja zaraz pomoże."
        await channel.send(embed=embed, view=TicketCloseView())
        await interaction.response.send_message(f"✅ Otwarto ticket: {channel.mention}", ephemeral=True)

    @discord.ui.button(label="Rekrutacja", style=discord.ButtonStyle.green, custom_id="t_req")
    async def req(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "rekrutacja")

    @discord.ui.button(label="Zgłoś Cheatera", style=discord.ButtonStyle.danger, custom_id="t_cheat")
    async def cheat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "cheater")

    @discord.ui.button(label="Inna Sprawa", style=discord.ButtonStyle.gray, custom_id="t_other")
    async def other(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.create_ticket(interaction, "sprawa")

class TicketCloseView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="🔒 Zamknij", style=discord.ButtonStyle.red, custom_id="t_close")
    async def close(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.channel.delete()

# --- SYSTEM WERYFIKACJI ---
class VerifyView(discord.ui.View):
    def __init__(self): super().__init__(timeout=None)
    @discord.ui.button(label="✅ Weryfikacja", style=discord.ButtonStyle.success, custom_id="v_btn")
    async def verify(self, interaction: discord.Interaction, button: discord.ui.Button):
        role = interaction.guild.get_role(VERIFY_ROLE_ID)
        if role:
            await interaction.user.add_roles(role)
            await interaction.response.send_message("✅ Pomyślnie zweryfikowano! Nadano rangę Gracz.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Błąd: Nie znaleziono rangi Gracz.", ephemeral=True)

# --- KLASA BOTA ---
class MintBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.all())

    async def setup_hook(self):
        self.add_view(VerifyView())
        self.add_view(TicketTypeView())
        self.add_view(TicketCloseView())
        await self.tree.sync()
        print("✅ Systemy Mint.mc gotowe!")

bot = MintBot()

@bot.event
async def on_member_join(member):
    channel = bot.get_channel(WELCOME_CHANNEL_ID)
    if channel:
        embed = discord.Embed(
            title="Witamy na Mint.mc!",
            description=f"Siema {member.mention}! Pamiętaj, aby się zweryfikować na odpowiednim kanale!",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed)

# --- KOMENDY SLASH ---

@bot.tree.command(name="wiadomosc", description="Wysyła oficjalne ogłoszenie w obramowaniu")
@app_commands.checks.has_permissions(administrator=True)
async def msg(interaction: discord.Interaction, kanal: discord.TextChannel, tytul: str, tresc: str):
    embed = discord.Embed(title=tytul, description=tresc, color=discord.Color.blue())
    embed.set_footer(text="Mint.mc - Oficjalny komunikat", icon_url=bot.user.avatar.url if bot.user.avatar else None)
    await kanal.send(embed=embed)
    await interaction.response.send_message(f"✅ Ogłoszenie wysłane na {kanal.mention}", ephemeral=True)

@bot.tree.command(name="panele", description="Wysyła panele weryfikacji lub ticketów")
@app_commands.checks.has_permissions(administrator=True)
async def panels(interaction: discord.Interaction, typ: str):
    if typ == "ver":
        embed = discord.Embed(title="🛡️ Weryfikacja", description="Kliknij przycisk poniżej, aby otrzymać dostęp do serwera!", color=discord.Color.green())
        await interaction.channel.send(embed=embed, view=VerifyView())
    elif typ == "ticket":
        embed = discord.Embed(title="🎫 System Ticket", description="Wybierz kategorię zgłoszenia poniżej:", color=discord.Color.blue())
        await interaction.channel.send(embed=embed, view=TicketTypeView())
    await interaction.response.send_message("Panel wysłany.", ephemeral=True)

@bot.tree.command(name="zasady", description="Wysyła regulamin lub listę modów")
@app_commands.checks.has_permissions(administrator=True)
async def zasady(interaction: discord.Interaction, typ: str):
    if typ == "mody":
        embed = discord.Embed(title="📜 ZAKAZANE MODY", color=discord.Color.red())
        embed.add_field(name="❌ Zakazane:", value="• Cheat-Clienty\n• X-Ray / Freecam\n• KillAura / Reach\n• Baritone", inline=False)
        embed.add_field(name="✅ Dozwolone:", value="• OptiFine / Sodium\n• Replay Mod\n• Minimapa (bez graczy)", inline=False)
    elif typ == "regulamin":
        embed = discord.Embed(title="📋 REGULAMIN", description="1. Nie czituj.\n2. Nie obrażaj.\n3. Szanuj administrację.", color=discord.Color.blue())
    
    await interaction.channel.send(embed=embed)
    await interaction.response.send_message("Wysłano informację.", ephemeral=True)

if __name__ == "__main__":
    keep_alive()
    bot.run(TOKEN)
