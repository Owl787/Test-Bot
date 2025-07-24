import discord
from discord.ext import commands
from discord import app_commands
import re
import asyncio
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()
TOKEN = os.getenv("TOKEN")

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

auto_role_ids = {}  # Stores auto-role per server
spam_tracker = {}
SPAM_THRESHOLD = 3  # Messages within 5 seconds
SPAM_TIMEOUT = 60  # Seconds

# --- Events ---
@bot.event
async def on_ready():
    print(f"Bot is online: {bot.user}")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} slash commands.")
    except Exception as e:
        print(f"Error syncing commands: {e}")

@bot.event
async def on_member_join(member):
    role_id = auto_role_ids.get(member.guild.id)
    if role_id:
        role = member.guild.get_role(role_id)
        if role:
            await member.add_roles(role)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # Auto-delete link messages
    if re.search(r'https?://', message.content):
        await message.delete()

    # Spam detection
    uid = message.author.id
    now = message.created_at.timestamp()
    spam_tracker.setdefault(uid, []).append(now)
    spam_tracker[uid] = [t for t in spam_tracker[uid] if now - t <= 5]
    if len(spam_tracker[uid]) > SPAM_THRESHOLD:
        await message.delete()
        try:
            await message.author.timeout(timedelta(seconds=SPAM_TIMEOUT), reason="Spamming")
        except:
            pass

    await bot.process_commands(message)

# --- Slash Commands ---

@bot.tree.command(name="set-autorole", description="Set auto-role for new members")
@app_commands.describe(role="Role to give to new members")
async def set_autorole(interaction: discord.Interaction, role: discord.Role):
    auto_role_ids[interaction.guild.id] = role.id
    await interaction.response.send_message(f"Auto-role set to {role.name}", ephemeral=True)

@bot.tree.command(name="give-role", description="Give a role to a user")
@app_commands.describe(member="Member to give the role", role="Role to assign")
async def give_role(interaction: discord.Interaction, member: discord.Member, role: discord.Role):
    await member.add_roles(role)
    await interaction.response.send_message(f"Gave {role.name} to {member.mention}", ephemeral=True)

@bot.tree.command(name="kick", description="Kick a member")
@app_commands.describe(member="Member to kick", reason="Reason for kick")
async def kick(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.kick(reason=reason)
    await interaction.response.send_message(f"Kicked {member.mention}", ephemeral=True)

@bot.tree.command(name="ban", description="Ban a member")
@app_commands.describe(member="Member to ban", reason="Reason for ban")
async def ban(interaction: discord.Interaction, member: discord.Member, reason: str = "No reason"):
    await member.ban(reason=reason)
    await interaction.response.send_message(f"Banned {member.mention}", ephemeral=True)

@bot.tree.command(name="unban", description="Unban a user by ID")
@app_commands.describe(user_id="ID of the user to unban")
async def unban(interaction: discord.Interaction, user_id: str):
    user = await bot.fetch_user(int(user_id))
    await interaction.guild.unban(user)
    await interaction.response.send_message(f"Unbanned {user.mention}", ephemeral=True)

@bot.tree.command(name="timeout", description="Timeout a user")
@app_commands.describe(member="User to timeout", duration="e.g. 1d, 10min, 2m, 1y", reason="Reason")
async def timeout(interaction: discord.Interaction, member: discord.Member, duration: str, reason: str = "No reason"):
    seconds = parse_duration(duration)
    if seconds is None:
        await interaction.response.send_message("Invalid duration format. Use 1d, 10min, 1y, etc.", ephemeral=True)
        return
    await member.timeout(timedelta(seconds=seconds), reason=reason)
    await interaction.response.send_message(f"Timed out {member.mention} for {duration}", ephemeral=True)

def parse_duration(time_str):
    time_str = time_str.lower()
    total_seconds = 0
    matches = re.findall(r"(\d+)([a-z]+)", time_str)
    units = {
        "d": 86400, "day": 86400,
        "m": 2592000, "month": 2592000,
        "y": 31536000, "year": 31536000,
        "min": 60, "minute": 60,
        "h": 3600, "s": 1
    }
    for value, unit in matches:
        if unit not in units:
            return None
        total_seconds += int(value) * units[unit]
    return total_seconds

@bot.tree.command(name="clear", description="Clear a number of messages")
@app_commands.describe(amount="Number of messages to delete")
async def clear(interaction: discord.Interaction, amount: int):
    await interaction.channel.purge(limit=amount)
    await interaction.response.send_message(f"Deleted {amount} messages", ephemeral=True)

@bot.tree.command(name="move", description="Move a member to a voice channel")
@app_commands.describe(member="Member to move", vc="Voice channel to move them to")
async def move(interaction: discord.Interaction, member: discord.Member, vc: discord.VoiceChannel):
    await member.move_to(vc)
    await interaction.response.send_message(f"Moved {member.mention} to {vc.name}", ephemeral=True)

@bot.tree.command(name="delete-msg", description="Delete a message by ID")
@app_commands.describe(message_id="ID of the message to delete")
async def delete_msg(interaction: discord.Interaction, message_id: str):
    try:
        msg = await interaction.channel.fetch_message(int(message_id))
        await msg.delete()
        await interaction.response.send_message("Message deleted.", ephemeral=True)
    except:
        await interaction.response.send_message("Could not delete message.", ephemeral=True)

# --- Run Bot ---
bot.run(TOKEN)
