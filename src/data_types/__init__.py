from dataclasses import dataclass
from typing import Optional

import discord

GameId = str
UserId = int
MessageId = int


@dataclass
class DiscordMessage:
    content: str
    ephemeral: bool = True
    view: Optional[discord.ui.View] = None
    embed: Optional[discord.Embed] = None

    def for_send(self):
        return {
            item: value for item, value in self.__dict__.items() if value is not None
        }
