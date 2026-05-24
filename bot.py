import os
import discord
from discord import app_commands
import requests

BOT_TOKEN = os.environ.get('DISCORD_BOT_TOKEN')
PORT = os.environ.get('PORT', 5000)

class MyClient(discord.Client):
    def __init__(self):
        super().__init__(intents=discord.Intents.default())
        self.tree = app_commands.CommandTree(self)

    async def on_ready(self):
        print(f'Bot zalogowany jako {self.user}')
        try:
            await self.tree.sync()
            print("Komendy zsynchronizowane.")
        except Exception as e:
            print(f"Błąd synchronizacji: {e}")

bot_client = MyClient()

@bot_client.tree.command(name="link", description="Generuje zmaskowany link typu logger")
@app_commands.describe(url="Wklej oryginalny adres URL")
async def link(interaction: discord.Interaction, url: str):
    await interaction.response.defer(ephemeral=True)
    
    # Komunikacja lokalna z serwerem Flask działającym obok
    local_url = f"http://127.0.0.1:{PORT}/generate"
    
    try:
        response = requests.post(local_url, json={"originalUrl": url}, timeout=5)
        if response.status_code == 200:
            logger_url = response.json().get("loggerUrl")
            await interaction.followup.send(content=f"🟢 **Link wygenerowany:**\n`{logger_url}`", ephemeral=True)
        else:
            await interaction.followup.send(content="🔴 Serwer Flask zwrócił błąd.", ephemeral=True)
    except Exception as e:
        await interaction.followup.send(content=f"🔴 Brak komunikacji z backendem: {e}", ephemeral=True)

if __name__ == '__main__':
    if BOT_TOKEN:
        bot_client.run(BOT_TOKEN)
    else:
        print("🚨 BŁĄD: Brak zmiennej DISCORD_BOT_TOKEN!")
