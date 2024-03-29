import json
import logging
import discord
from discord.ext.commands import bot, command
import validators
from urllib.parse import urlparse, ParseResult
import yt_dlp
import os
import yaml


class Bot(discord.ext.commands.Bot):
    video_netlocs = ["youtu.be"]

    def __init__(self, token: str):
        # define intents
        intents = discord.Intents.default()
        intents.message_content = True

        # load bot config
        with open('config.yaml', 'r') as f:
            self.cfg = yaml.safe_load(f)

        # init youtube downloader config
        self.ytdl_config = {
            'logger': logging.getLogger(),
            'paths': {'home': self.cfg.get('archive_path')},
            'download_archive': os.path.join(self.cfg.get('archive_path'), '.archive'),
            'progress_hooks': [self.video_progress_hook],
        }

        # init base client class
        super().__init__(command_prefix=self.cfg.get('command_prefix'), intents=intents)

        # run client
        super().run(token=token)

    async def on_ready(self):
        logging.info(f"Ready from {self.user}!")
        for channel_name in self.cfg.get('archive_channels'):
            channel = discord.utils.get(self.get_all_channels(), name=channel_name)  # guild__name='Cool', name='general'
            async for msg in channel.history(limit=100, oldest_first=False,):
                await self.process_message(msg)

    async def on_message(self, message):
        await self.process_message(message)

    async def process_message(self, message):
        # check for bot messages
        if message.author == self.user:
            return

        # check if message is from configured channel(s)
        if len(self.cfg.get('archive_channels')) and str(message.channel) not in self.cfg.get('archive_channels'):
            return

        # is this message an url?
        if self.is_url(message.content):
            parsed_url = urlparse(message.content)
            logging.info(parsed_url)

            # is this a video url?
            if self.is_video_url(parsed_url):
                # await message.clear_reactions()
                success = self.download_video(message.content)
                if success:
                    await message.add_reaction("✅")
                else:
                    await message.add_reaction("❌")

        if message.content.startswith("$hello"):
            await message.channel.send("Hello!")

    @classmethod
    def is_url(cls, text: str) -> bool:
        return validators.url(text)

    @classmethod
    def is_video_url(cls, result: ParseResult) -> bool:
        return result.netloc in cls.video_netlocs

    def download_video(self, url: str) -> bool:
        """
        Attempts to download video from given url.
        Returns true if successful.
        """
        # TODO is youtube video?
        try:
            with yt_dlp.YoutubeDL(self.ytdl_config) as ydl:
                # extract video info
                info = ydl.extract_info(url, download=False)

                # download video
                err = ydl.download(url)
                return not err
        except Exception as e:
            logging.error(e)
            return False

    @classmethod
    def video_progress_hook(cls, d):
        logging.info(f"{d['_percent_str']} # {d['filename']}")
