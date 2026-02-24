import discord
import os
import sys

# Add repo root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from node.node import Node

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True

client = discord.Client(intents=intents)

node = Node()

@client.event
async def on_ready():
    print(f"Agent Lab online as {client.user}")

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    content = message.content.strip()

    if content.startswith("/node"):
        response = node.handle(content)
        await message.channel.send(response)

client.run(TOKEN)

