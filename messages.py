"""messages.py contains the bot's introduction and the error message."""

import config


def introduction(guild_id):
    """Returns a string introducing the bot."""
    intro = INTRO.format(config.name) + "\n\n" + USAGE
    if guild_id not in config.servers_no_reacts:
        intro += "\n" + REACTS
    intro += "\n" + PREVENT
    if guild_id not in config.servers_no_deletion:
        intro += "\n" + DELETE
    intro += "\n" + HELP
    return intro


INTRO = """Hello, I'm Fanfiction Abstractor! I provide information about fanfiction\
 on AO3 and FFN. Please contact {} with questions or comments about the bot.
Please note the bot does not provide information about AO3 archive-locked works."""

USAGE = "To use the bot, send a message containing a link to an AO3 or FFN work or series."
REACTS = "To get information about a fic in the series, react with the fic's number."
PREVENT = "To prevent the bot from posting, put ! immediately before a link."
DELETE = "To delete a bot message, reply to it with the message \"delete\"."
HELP = "To trigger this message, tag me and say \"help\" or \"info\"."

ERROR_MESSAGE = """Error on {}.
If you can access the page in your browser, please @ {}."""
