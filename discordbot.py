import json
import os
import io
import discord
from PIL import Image
from pathlib import Path
import re
import base64
from discord.ext import commands
from discord.ext.commands import Bot
import asyncio
import random
import shutil
from datetime import datetime, timedelta
import sys
# get .env variables



if __name__ == '__main__':
    if len(sys.argv) < 4:
        print('Usage: python discordbot.py <DISCORD_BOT_TOKEN> <ENDPOINT> <CHANNEL_ID>')
        sys.exit(1)
    DISCORD_BOT_TOKEN = sys.argv[1]
    ENDPOINT = sys.argv[2]
    CHANNEL_ID = sys.argv[3]
# Access environment variables like this



intents = discord.Intents.all()
bot = Bot(command_prefix="/", intents=intents, help_command=None)
bot.endpoint = ENDPOINT
bot.chatlog_dir = "chatlog_dir"
bot.endpoint_connected = False
bot.channel_id = CHANNEL_ID
bot.guild_ids = [int(x) for x in sys.argv[3].split(",")]
bot.debug = True
bot.char_name = ""
characters_folder = 'Characters'
cards_folder = 'Cards'
characters = []

def upload_character(json_file, img, tavern=False):
    json_file = json_file if type(json_file) == str else json_file.decode('utf-8')
    data = json.loads(json_file)
    outfile_name = data["char_name"]
    i = 1
    while Path(f'{characters_folder}/{outfile_name}.json').exists():
        outfile_name = f'{data["char_name"]}_{i:03d}'
        i += 1
    if tavern:
        outfile_name = f'TavernAI-{outfile_name}'
    with open(Path(f'{characters_folder}/{outfile_name}.json'), 'w') as f:
        f.write(json_file)
    if img is not None:
        img = Image.open(io.BytesIO(img))
        img.save(Path(f'{characters_folder}/{outfile_name}.png'))
    print(f'New character saved to "{characters_folder}/{outfile_name}.json".')
    return outfile_name


def upload_tavern_character(img, name1, name2):
    _img = Image.open(io.BytesIO(img))
    _img.getexif()
    decoded_string = base64.b64decode(_img.info['chara'])
    _json = json.loads(decoded_string)
    _json = {"char_name": _json['name'], "char_persona": _json['description'], "char_greeting": _json["first_mes"], "example_dialogue": _json['mes_example'], "world_scenario": _json['scenario']}
    _json['example_dialogue'] = _json['example_dialogue'].replace('{{user}}', name1).replace('{{char}}', _json['char_name'])
    return upload_character(json.dumps(_json), img, tavern=True)


# CONVERT CARDS
# Check the Cards folder for cards and convert them to characters
try:
    for filename in os.listdir(cards_folder):
        if filename.endswith('.png'):
            with open(os.path.join(cards_folder, filename), 'rb') as read_file:
                img = read_file.read()
                name1 = 'User'
                name2 = 'Character'
                tavern_character_data = upload_tavern_character(img, name1, name2)
            with open(os.path.join(characters_folder, tavern_character_data + '.json')) as read_file:
                character_data = json.load(read_file)
                # characters.append(character_data)
            read_file.close()
            if not os.path.exists(f"{cards_folder}/Converted"):
                os.makedirs(f"{cards_folder}/Converted")
            os.rename(os.path.join(cards_folder, filename), os.path.join(f"{cards_folder}/Converted/", filename))
except:
    pass


# Load character data from JSON files in the character folder
for filename in os.listdir(characters_folder):
    if filename.endswith('.json'):
        with open(os.path.join(characters_folder, filename)) as read_file:
            character_data = json.load(read_file)
            # Add the filename as a key in the character data dictionary
            character_data['char_filename'] = filename
            # Check if there is a corresponding image file for the character
            image_file_jpg = f"{os.path.splitext(filename)[0]}.jpg"
            image_file_png = f"{os.path.splitext(filename)[0]}.png"
            if os.path.exists(os.path.join(characters_folder, image_file_jpg)):
                character_data['char_image'] = image_file_jpg
            elif os.path.exists(os.path.join(characters_folder, image_file_png)):
                character_data['char_image'] = image_file_png
            characters.append(character_data)

# Character selection
# Check if chardata.json exists
if os.path.exists('chardata.json'):
    with open("chardata.json") as read_file:
        character_data = json.load(read_file)
    # Prompt the user to use the same character
    print(f"Last Character used: {character_data['char_name']}")
    # Set up the timer
    try:
        answer = input(f"\nUse this character? (y/n) [y]: ")
    except:
        answer = "y"

else:
    answer = "n"

if answer.lower() == "n":
    for i, character in enumerate(characters):
        print(f"{i+1}. {character['char_name']}")
    selected_char = None
    while selected_char is None:
        try:
            selected_char = int(input(f"\n\nPlease select a character: ")) - 1
            if selected_char < 0 or selected_char >= len(characters):
                raise ValueError
        except ValueError:
            print("Invalid input. Please enter a number between 1 and", len(characters))
            selected_char = None
    data = characters[selected_char]
    update_name = None
    while update_name not in ["y", "n"]:
        update_name = input("Update Bot name and pic? (y or n): ").lower()
        if update_name not in ["y", "n"]:
            print("Invalid input. Please enter 'y' or 'n'.")
    # Get the character name, greeting, and image
    char_name = data["char_name"]
    char_filename = os.path.join(characters_folder, data['char_filename'])
    char_image = data.get("char_image")
    shutil.copyfile(char_filename, "chardata.json")
    bot.json_file = "chardata.json"
else:
    update_name = "n"

with open("chardata.json") as read_file:
    character_data = json.load(read_file)
    bot.user_name = character_data["char_name"]

@bot.event
async def on_ready():
    if update_name.lower() == "y":
        try:
            with open(f"Characters/{char_image}", 'rb') as f:
                avatar_data = f.read()
            await bot.user.edit(username=char_name, avatar=avatar_data)
        except FileNotFoundError:
            with open(f"Characters/default.png", 'rb') as f:
                avatar_data = f.read()
            await bot.user.edit(username=char_name, avatar=avatar_data)
            print(f"No image found for {char_name}. Setting image to default.")
        except discord.errors.HTTPException as error:
            if error.code == 50035 and 'Too many users have this username, please try another' in error.text:
                await bot.user.edit(username=char_name + "BOT", avatar=avatar_data)
            elif error.code == 50035 and 'You are changing your username or Discord Tag too fast. Try again later.' in error.text:
                pass
            else:
                raise error



async def get_last_messages(channel, limit=10):
    messages = []
    async for message in channel.history(limit=limit):
        messages.append(message)
        if message.author == channel.guild.me:
            break
    coroutines = [channel.fetch_message(id) for id in [msg.id for msg in messages[:-1]]]
    results = await asyncio.gather(*coroutines)
    formatted_messages = [f"{message.author.name}: {message.clean_content}" for message in reversed(results)]
    return '\n'.join(formatted_messages)

async def get_user_messages(channel, message_author, limit=10):
    messages = []
    async for message in channel.history(limit=limit):
        if message.author == bot.user:
            break
        if message.author == message_author:
            messages.append(message)
    coroutines = [channel.fetch_message(id) for id in [msg.id for msg in messages[:-1]]]
    results = await asyncio.gather(*coroutines)
    formatted_messages = [f"{message.author.name}: {message.clean_content}" for message in
                          reversed(results)]
    return '\n'.join(formatted_messages)




stop_names = [bot.user_name]
async def on_message(message):
    # if message starts with ".", "/"" or is by the bot - do nothing
    if message.author == bot.user_name or message.clean_content.startswith((".", "/")):
        return

    # Add new message.author.name to stop_names list if they are not in there already to use for splitting messages
    if message.author.name not in stop_names:
        stop_names.append(message.author.name)

    # Check if the message is sent in a server or a private message
    if message.channel.id in CHANNEL_ID or message.guild is None:
        message_content = message.clean_content
        # Get the message content and the bot's name for pattern matching
        content = message.clean_content.lower()
        name_pattern = r"(\b|^){}(\b|$)".format(bot.user.name.split()[0].lower())
        if message.reference is not None:
            pass


bot.event(on_message)


async def has_image_attachment(message_content):
    url_pattern = re.compile(r'http[s]?://[^\s/$.?#].[^\s]*\.(jpg|jpeg|png|gif)', re.IGNORECASE)
    tenor_pattern = re.compile(r'https://tenor.com/view/[\w-]+')
    for attachment in message_content.attachments:
        if attachment.filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            return True
        # Check if the message content contains a URL that ends with an image file extension
    if url_pattern.search(message_content.content):
        return True
    # Check if the message content contains a Tenor GIF URL

    elif tenor_pattern.search(message_content.content):
        return True
    else:
        return False


bot.current_message = ""
async def has_image_attachment(message):
    url_pattern = re.compile(r'http[s]?://[^\s/$.?#].[^\s]*\.(jpg|jpeg|png|gif)', re.IGNORECASE)
    tenor_pattern = re.compile(r'https://tenor.com/view/[\w-]+')
    for attachment in message.attachments:
        if attachment.filename.lower().endswith((".jpg", ".jpeg", ".png", ".gif")):
            return True
    # Check if the message content contains a URL that ends with an image file extension
    if url_pattern.search(message.clean_content):
        return True
    # Check if the message content contains a Tenor GIF URL
    elif tenor_pattern.search(message.clean_content):
        return True
    else:
        return False


bot.current_message = ""
async def check_for_new_messages(channel, last_message_time):
    channel = bot.get_channel(channel)
    stop_names = []  # Initialize stop_names list
    while True:
        # print("Checking for new messages...")
        await asyncio.sleep(10 + random.randint(5, 10))  # Check every 60 seconds with random delay

        # Get the timestamp of the last bot message in the channel
        async for message in channel.history(limit=5):
            if message.author == bot.user:
                last_message_time = message.created_at
                break

        messages = [message async for message in channel.history(limit=None, after=last_message_time) if message.author != bot.user]

        formatted_messages = []
        for message in messages:
            if message .clean_content.startswith((".", "/")):
                continue
            if await has_image_attachment(message):
                image_caption = await bot.get_cog("image_caption").image_comment(message, message.clean_content)
                message_content = f"{image_caption}"
            else:
                message_content = message.clean_content

            formatted_message = f"{message.author.name}: {message_content}"
            formatted_messages.append(formatted_message)

            if message.author.name not in stop_names:
                stop_names.append(message.author.name)

        if len(formatted_messages) > 0:
            new_messages = []
            for message in formatted_messages:
                for stop_name in stop_names:
                    if message.startswith(stop_name + ': '):
                        if bot.current_message and bot.current_message not in new_messages:
                            new_messages.append(bot.current_message)
                        bot.current_message = message
                        break
                    else:
                        bot.current_message += message
            if bot.current_message and bot.current_message not in new_messages:
                new_messages.append(bot.current_message)

            response = await bot.get_cog("chatbot").batch_chat_command("\n".join(new_messages), channel)

            async with channel.typing():
                await asyncio.sleep(1)  # Simulate some work being done
                await channel.send(response)
                bot.current_message = ""
        last_message_time = datetime.now()



async def load_cogs() -> None:
    for file in os.listdir(f"{os.path.realpath(os.path.dirname(__file__))}/cogs"):
        if file.endswith(".py"):
            extension = file[:-3]
            try:
                await bot.load_extension(f"cogs.{extension}")
            except Exception as e:
                exception = f"{type(e).__name__}: {e}"
                print(exception)




asyncio.run(load_cogs())

bot.run(DISCORD_BOT_TOKEN)
