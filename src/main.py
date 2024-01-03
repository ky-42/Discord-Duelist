"""Used to run bot"""

import os

from dotenv import load_dotenv

from bot import bot


def main():
    # Gets token from env and runs bot with it
    load_dotenv()
    token = os.getenv("DISCORD_TOKEN")
    if token:
        bot.run(token)
    else:
        print("Please set DISCORD_TOKEN in .env")


if __name__ == "__main__":
    main()
