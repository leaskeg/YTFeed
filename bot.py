import discord
from discord.ext import tasks
import requests
import json
import config
import re

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

client = discord.Bot(intents=intents)

# Dictionary to store mappings of YouTube channels to Discord channels
channel_mappings = {}

@client.event
async def on_ready():
    print(f'Bot is ready as {client.user}')
    check_new_videos.start()

def is_valid_youtube_url(url):
    """Validate if the provided URL is a valid YouTube channel URL"""
    pattern = re.compile(r'(https?://)?(www\.)?(youtube|youtu|youtube-nocookie)\.(com|be)/(channel/|@)?[A-Za-z0-9\-_]+')
    return pattern.match(url) is not None

@client.slash_command(description="Set YouTube and Discord channels for video updates")
async def setchannel(ctx, youtube_url: str, discord_channel: discord.TextChannel):
    """Command to set the YouTube channel to be tracked and the Discord channel to post updates"""
    if not is_valid_youtube_url(youtube_url):
        await ctx.respond("Invalid YouTube URL. Please provide a valid YouTube channel URL.")
        return

    channel_mappings[youtube_url] = discord_channel.id
    await ctx.respond(f"Set YouTube channel {youtube_url} to post updates in Discord channel {discord_channel.mention}")

def get_latest_video(youtube_url):
    """Fetch the latest video from the specified YouTube channel"""
    # Extract the channel ID or name from the URL
    match = re.search(r'(channel/|@)([A-Za-z0-9\-_]+)', youtube_url)
    if not match:
        return None, None
    channel_id = match.group(2)

    # Determine whether the identifier is a channel ID or a custom name
    if channel_id.startswith('UC'):
        url = f"https://www.googleapis.com/youtube/v3/search?key={config.YOUTUBE_API_KEY}&channelId={channel_id}&part=snippet,id&order=date&maxResults=1"
    else:
        url = f"https://www.googleapis.com/youtube/v3/search?key={config.YOUTUBE_API_KEY}&forUsername={channel_id}&part=snippet,id&order=date&maxResults=1"

    response = requests.get(url)
    data = response.json()
    if "items" in data:
        video_id = data['items'][0]['id']['videoId']
        video_title = data['items'][0]['snippet']['title']
        video_url = f"https://www.youtube.com/watch?v={video_id}"
        return video_title, video_url
    return None, None

@tasks.loop(seconds=config.CHECK_INTERVAL)
async def check_new_videos():
    """Background task to check for new videos and post updates"""
    for youtube_url, discord_channel_id in channel_mappings.items():
        video_title, video_url = get_latest_video(youtube_url)
        if video_title and video_url:
            discord_channel = client.get_channel(discord_channel_id)
            if discord_channel:
                await discord_channel.send(f"New video uploaded: {video_title}\nWatch here: {video_url}")

client.run(config.DISCORD_BOT_TOKEN)
