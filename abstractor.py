"""Abstractor is the discord client class.

This class contains the bot's handling of discord events.
"""

import cloudscraper
import config
import discord
import logging
import messages
import parser
import re
import traceback

# Import the logger from another file
logger = logging.getLogger('discord')

# The regular expressions to identify AO3 and FFN links.
# Note there may be an extra character at the beginning, due to checking
# the previous character to verify it is not ! (which would not match)
AO3_MATCH = re.compile(
    "(^|[^!])https?:\\/\\/(www\\.)?archiveofourown.org(\\/collections\\/\\w+)?\\/(works|series)\\/\\d+")
FFN_MATCH = re.compile(
    "(^|[^!])https?:\\/\\/(www\\.|m.)?fanfiction.net\\/s\\/\\d+")


class Abstractor(discord.Client):
    """The discord bot client itself."""

    async def on_ready(self):
        """When starting bot, print the servers it is part of."""
        s = "Logged on!\nMember of:\n"
        for guild in self.guilds:
            owner = await self.fetch_user(guild.owner_id)
            s += "{}\t{}\t{}\t{}\n".format(
                guild.id, guild.name, owner, guild.owner_id)
        logger.info(s)

    async def on_guild_join(self, guild):
        """Print a message when the bot is added to a server."""
        s = "Joined a new guild!\n"
        owner = await self.fetch_user(guild.owner_id)
        s = "\t".join((guild.id, guild.name, owner, guild.owner_id))

    async def on_guild_remove(self, guild):
        """Print a message when the bot is removed a server."""
        s = "Removed from a guild."
        owner = await self.fetch_user(guild.owner_id)
        s = "\t".join((guild.id, guild.name, owner, guild.owner_id))

    async def on_message(self, message):
        """Parse messages and respond if they contain a fanfiction link."""
        # ignore own messages
        if message.author == self.user:
            return
        # ignore Fanfic Rec Bot
        if message.author.id in config.bots_ignore:
            return

        # post a greeting if tagged
        content = message.content.lower()
        if "<@!847700548136075305>" in content or "<@847700548136075305>" \
                in content or "<@&849177654682320898>" in content:
            if "help" in content or "info" in content:
                output = messages.introduction(message.guild.id)
                await message.channel.send(output)

        # check for AO3 links
        ao3_links = AO3_MATCH.finditer(content)
        links_processed = set()
        max_links = 1
        num_processed = 0
        for link in ao3_links:
            if num_processed >= max_links:
                break
            else:
                num_processed += 1
            # clean up link
            link = link.group(0).replace("http://", "https://")\
                .replace("www.", "")
            # regex match may include an extra character at the start
            if not link.startswith("https://"):
                link = link[1:]
            # do not link a fic more than once per message
            if link in links_processed:
                continue
            # Strip "collection from URL before checking for duplicate links.
            base_link = link
            if "/collections/" in base_link:
                base_link = link.split("/")
                base_link.pop(3)
                base_link.pop(3)
                base_link = "/".join(base_link)
            links_processed.add(base_link)

            # Attempt to get summary of AO3 work or series
            output = ""
            async with message.channel.typing():
                try:
                    if "/works/" in link:
                        output = parser.generate_ao3_work_summary(link)
                    elif "/series/" in link:
                        output = parser.generate_ao3_series_summary(link)
                # if the process fails for an unhandled reason, print error
                except Exception:
                    logger.exception("Failed to get AO3 summary")
            if len(output) > 0:
                await message.channel.send(output)

        # Check for FFN links
        ffn_links = FFN_MATCH.finditer(content)
        for link in ffn_links:
            if num_processed >= max_links:
                break
            else:
                num_processed += 1
            # Standardize link format
            if "m.fanfiction.net" in link.group(0):
                mobile = True
            else:
                mobile = False
            link = link.group(0).replace(
                "http://", "https://").replace("m.", "www.")
            link = link.replace(
                "https://fanfiction.net", "https://www.fanfiction.net")
            if not link.startswith("https://"):
                link = link[1:]
            # If a fic is linked multiple times, only send one message
            if link in links_processed:
                continue
            links_processed.add(link)

            # Generate the summary and send it
            output = ""
            async with message.channel.typing():
                try:
                    output = parser.generate_ffn_work_summary(link)
                # We can't resolve cloudflare errors
                # but if the link was a mobile link, send the normal one
                except cloudscraper.exceptions.CloudflareException:
                    if mobile:
                        output = link
                except Exception:
                    logger.exception("Failed to get FFN summary")
            if len(output) > 0:
                await message.channel.send(output)

        # if a bot message is replied to with "delete", delete the message
        if message.guild.id not in config.servers_no_deletion:
            if message.reference and message.reference.resolved:
                if message.reference.resolved.author == self.user:
                    if message.content == "delete":
                        await message.reference.resolved.delete()

    async def on_reaction_add(self, reaction, user):
        """If react is added to bot's series message, send work information.

        This can be disabled per server in config.py.
        """
        if reaction.message.guild.id in config.servers_no_reacts:
            return
        if reaction.message.author != self.user or reaction.count != 1:
            return
        content = reaction.message.content
        if "https://archiveofourown.org/series/" not in content.split("\n")[0]:
            return
        fic = parser.REACTS.get(reaction.emoji)
        if not fic:
            return
        series = AO3_MATCH.search(content).group(0)
        # regex match may include an extra character at the start
        if not series.startswith("https://"):
            series = series[1:]
        link = "https://archiveofourown.org"\
            + parser.identify_work_in_ao3_series(series, fic)
        if link:
            output = ""
            async with reaction.message.channel.typing():
                try:
                    output = parser.generate_ao3_work_summary(link)
                except Exception:
                    logger.exception("Failed to generate summary for work in series")
            if len(output) > 0:
                await reaction.message.channel.send(output)
