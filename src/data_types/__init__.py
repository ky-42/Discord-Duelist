"""Contains data types used throughout program"""

from dataclasses import dataclass
from enum import Enum
from typing import Optional

import discord

# Type aliases
GameId = str
UserId = int
MessageId = int


class GameResult(Enum):
    """Enum for game results (win, tie, loss)"""

    WON = 0
    TIED = 1
    LOST = 2


@dataclass
class DiscordMessage:
    """Stores data for a message to be sent to Discord.

    Attributes:
        content (str): Content of message.
        ephemeral (bool): Whether message is only visible to user its sent to.
        view (Optional[discord.ui.View]): View to be attached to message.
        embed (Optional[discord.Embed]): Embed to be attached to message.
    """

    content: str
    ephemeral: bool = True
    view: Optional[discord.ui.View] = None
    embed: Optional[discord.Embed] = None

    def for_send(self) -> dict:
        """Creates a dictionary of attributes for sending to Discord.

        Removes any attributes with a value of None.

        Returns:
            dict: Dictionary of attributes.
        """
        return {
            item: value for item, value in self.__dict__.items() if value is not None
        }
