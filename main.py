import os
import random
import time
import discord
from discord import app_commands

# --- KONFIGURACJA ID RÓL (Wklej tutaj ID ze swojego serwera) ---
ROLE_PRO_ID = 1512520808839381012  # Zmień na prawdziwe ID (jako liczba, bez cudzysłowu)
ROLE_ULTRA_ID = 1512520692015562812  # Zmień na prawdziwe ID (jako liczba, bez cudzysłowu)

# --- CZASY COOLDOWNÓW (w sekundach) ---
CD_UZER = 5 * 60 * 60  # 5 godzin
CD_PRO = 30 * 60       # 30 minut
CD_ULTRA = 30          # 30 sekund

# Słownik do przechowywania cooldownów
cooldowns = {}

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def setup_hook(self):
        # Rejestracja komend slash globalnie
        await self.tree.sync()

client = MyClient()

def generate_random_code(template):
    chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
    result = ""
    for char in template:
        if char == 'X':
            result += random.choice(chars)
        else:
            result += char
    return result

def format_time(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    minutes = seconds // 60
    if minutes < 60:
        return f"{int(minutes)}m {int(seconds % 60)}s"
    hours = minutes // 60
    return f"{int(hours)}h {int(minutes % 60)}m"

@client.event
async def on_ready():
    print(f"Bot zalogowany na hostingu jako {client.user}")

# Funkcja pomocnicza do obsługi generatorów
async def handle_gen(interaction: discord.Interaction, game_name, template):
    user = interaction.user
    member = interaction.guild.get_member(user.id)
    
    # Ustalanie rangi i czasu cooldownu
    user_cooldown_duration = CD_UZER
    rank_name = "UZER"

    if member:
        role_ids = [role.id for role in member.roles]
        if ROLE_ULTRA_ID in role_ids:
            user_cooldown_duration = CD_ULTRA
            rank_name = "ULTRA"
        elif ROLE_PRO_ID in role_ids:
            user_cooldown_duration = CD_PRO
            rank_name = "PRO"

    # Sprawdzanie cooldownu
    cooldown_key = f"{user.id}-{interaction.command.name}"
    now = time.time()

    if cooldown_key in cooldowns:
        expiration_time = cooldowns[cooldown_key] + user_cooldown_duration
        if now < expiration_time:
            time_left = expiration_time - now
            error_embed = discord.Embed(
                title="Limit wyczerpany!",
                description=f"Twoja ranga to **{rank_name}**. Mozesz wygenerowac kolejny kod dopiero za:\n⏳ **{format_time(time_left)}**",
                color=discord.Color.red()
            )
            error_embed.set_footer(text="Chcesz generowac czesciej? Kup wyzsza range!")
            await interaction.response.send_message(embed=error_embed, ephemeral=True)
            return

    # Generowanie kodu
    code = generate_random_code(template)
    
    # Tworzenie embeda na PV
    dm_embed = discord.Embed(
        title=f"KOD {game_name} WYGENEROWANY!",
        description=f"Tworzenie nowego kodu zakonczone sukcesem!\n\n**KOD:** ```{code}
```\n*Zrealizuj go jak najszybciej.*",
        color=discord.Color.green()
    )
    dm_embed.add_field(name="Uzyta ranga", value=f"`{rank_name}`", inline=True)
    dm_embed.add_field(name="Status kodu", value="Aktywny", inline=True)
    dm_embed.set_footer(text="Dzieki za korzystanie z bazy!")

    try:
        # Wysyłanie wiadomości prywatnej (PV)
        await user.send(embed=dm_embed)

        # Sukces na kanale publicznym
        success_embed = discord.Embed(
            title="Kod wyslany!",
            description=f"Hej {user.mention}, wygenerowano nowy kod i wyslano go w wiadomosci prywatnej (PV)! Sprawdz DM.",
            color=discord.Color.green()
        )
        success_embed.set_footer(text=f"Ranga: {rank_name} - Nastepny za: {format_time(user_cooldown_duration)}")
        
        cooldowns[cooldown_key] = now
        await interaction.response.send_message(embed=success_embed)

    except discord.Forbidden:
        # Błąd jeśli użytkownik ma zablokowane DM
        error_channel_embed = discord.Embed(
            title="Blad wysylania!",
            description=f"Nie moglem wyslac kodu do Ciebie, {user.mention}.\n\nMasz zablokowane wiadomosci prywatne (DM) z tego serwera! Odblokuj je w ustawieniach i sprobuj ponownie.",
            color=discord.Color.red()
        )
        error_channel_embed.set_footer(text="Status: Blokada DM")
        await interaction.response.send_message(embed=error_channel_embed, ephemeral=True)

# --- KOMENDY SLASH ---

@client.tree.command(name="gen-mc", description="Generuje kod podarunkowy do Minecraft")
async def gen_mc(interaction: discord.Interaction):
    await handle_gen(interaction, "MINECRAFT", "XXXX-XXXX-XXXX")

@client.tree.command(name="gen-psc", description="Generuje kod zasilajacy PaySafeCard")
async def gen_psc(interaction: discord.Interaction):
    await handle_gen(interaction, "PAYSAFECARD", "XXXX-XXXX-XXXX-XXXX")

@client.tree.command(name="gen-roblox", description="Generuje kod na darmowe Robuxy")
async def gen_roblox(interaction: discord.Interaction):
    await handle_gen(interaction, "ROBLOX ROBUX", "XXXX-XXXX-XXXX")

@client.tree.command(name="setup-server", description="Automatycznie tworzy strukture kanalow i cennik rang")
@app_commands.checks.has_permissions(administrator=True)
async def setup_server(interaction: discord.Interaction):
    await interaction.response.send_message("Rozpoczynam budowanie struktury serwera... Prosze czekac.", ephemeral=True)
    guild = interaction.guild

    try:
        # Tworzenie Kategorii i kanałów
        main_category = await guild.create_category(name="GLOWNA STREFA")
        await guild.create_text_channel(name="regulamin", category=main_category)
        shop_channel = await guild.create_text_channel(name="cennik-rang", category=main_category)
        await guild.create_text_channel(name="dowody-legit", category=main_category)

        gen_category = await guild.create_category(name="DARMOWE KODY")
        await guild.create_text_channel(name="gen-minecraft", category=gen_category)
        await guild.create_text_channel(name="gen-roblox", category=gen_category)
        await guild.create_text_channel(name="gen-psc", category=gen_category)

        # Cennik
        price_embed = discord.Embed(
            title="SKLEP GENERATORA - OFERTA RANG",
            description="Chcesz generowac kody znacznie czesciej bez dlugiego czekania? Zdobadz wyzsza range i omin limity!",
            color=discord.Color.gold()
        )
        price_embed.add_field(name="Ranga: UZER", value="• **Cena:** `DARMOWA` (Dla kazdego)\n• Cooldown: **5 godzin** na komende\n• Dostep do podstawowych generatorow.", inline=False)
        price_embed.add_field(name="Ranga: PRO", value="• **Cena:** `10 PLN` (PSC / Blik)\n• Cooldown: **Skrocony do 30 minut!**\n• Wieksza szansa na trafienie kodu.", inline=False)
        price_embed.add_field(name="Ranga: ULTRA", value="• **Cena:** `25 PLN` (PSC / Blik)\n• Cooldown: **Zaledwie 30 sekund!**\n• Priorytetowe generowanie.", inline=False)
        price_embed.set_footer(text="W celu zakupu skontaktuj sie z Wlascicielem serwera poprzez Ticket / DM!")

        await shop_channel.send(embed=price_embed)
        await interaction.edit_original_response(content="Serwer zostal pomyslnie zbudowany!")

    except Exception as e:
        print(e)
        await interaction.edit_original_response(content="Wystapil blad podczas budowania serwera. Sprawdz uprawnienia bota.")

# Pobieranie tokenu ze zmiennych środowiskowych na hostingu
TOKEN = os.getenv("DISCORD_TOKEN")

if not TOKEN:
    print("BLAD: Brak zmiennej DISCORD_TOKEN w konfiguracji hostingu!")
    exit(1)

client.run(TOKEN)
