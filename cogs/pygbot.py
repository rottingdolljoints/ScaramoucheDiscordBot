import re
import json
import requests
import discord
from discord import app_commands
from discord.ext import commands
import os
import datetime
import os


now = datetime.datetime.now()
date_string = now.strftime("It is %A %B %d %Y at %I:%M %p")

# load environment variables
CHATLOG_DIR = "chatlog_dir"

model_config = {
    "use_story": False,
    "use_authors_note": False,
    "use_world_info": False,
    "use_memory": False,
    "max_context_length": 1405,
    "max_length": 1200,
    "rep_pen": 1.04,
    "rep_pen_range": 1024,
    "rep_pen_slope": 0.9,
    "temperature": 0.65,
    "tfs": 0.9,
    "top_k": 0,
    "top_a": 0,
    "top_p": 0.9,
    "typical": 1,
    "sampler_order": [6, 0, 1, 2, 3, 4, 5]
}

class Chatbot:
    def __init__(self, char_filename, bot):
        self.prompt = None
        self.endpoint = bot.endpoint
        # Send a PUT request to modify the settings
        requests.put(f"{self.endpoint}/config", json=model_config)
        # read character data from JSON file
        with open(char_filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.char_name = data["char_name"]
            self.char_persona = data["char_persona"]
            self.char_greeting = data["char_greeting"]
            self.world_scenario = data["world_scenario"]
            self.example_dialogue = data["example_dialogue"]
            self.endpoint = bot.endpoint
            requests.put(f"{self.endpoint}/config", json=model_config)
        # create chatlog directory if it doesn't exist
        if not os.path.exists(CHATLOG_DIR):
            os.makedirs(CHATLOG_DIR)

        # initialize conversation history and character information
        self.convo_filename = None
        self.conversation_history = ""
        self.character_info = f"{self.char_name}'s Persona: {self.char_persona}\nScenario: {self.world_scenario}\n{self.example_dialogue}\n"

        self.num_lines_to_keep = 20

    async def set_convo_filename(self, convo_filename):
        # set the conversation filename and load conversation history from file
        self.convo_filename = convo_filename
        if not os.path.isfile(convo_filename):
            # create a new file if it does not exist
            with open(convo_filename, "w", encoding="utf-8") as f:
                f.write("<START>\n")
        with open(convo_filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            num_lines = min(len(lines), self.num_lines_to_keep)
            self.conversation_history = "<START>\n" + "".join(lines[-num_lines:])


    async def batch_save_conversation(self, message_content, channel):
        # add user message to conversation history
        self.conversation_history += f"{message_content}\n"
        print(f"{message_content}\n")
        self.prompt = {
            "prompt": self.character_info + '\n'.join(
                self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + f'{self.char_name}:',
        }
        # send a post request to the API endpoint
        response = requests.post(f"{self.endpoint}/api/v1/generate", json=self.prompt)
        # check if the request was successful
        if response.status_code == 200:
            # Get the results from the response
            results = response.json()['results']
            print(f"results{results}")
            response_list = [line for line in results[0]['text'][1:].split("\n")]
            response_text = response_list[0]
            print(f"response_text{response_text}")

            # add bot response to conversation history
            self.conversation_history += f'{self.char_name}: {response_text}\n'
            print(f'{self.char_name}: {response_text}\n')
            with open(self.convo_filename, "a", encoding="utf-8") as f:
                f.write(f'{message_content}\n')
                f.write(f'{self.char_name}: {response_text}\n')
            return response_text


class ChatbotCog(commands.Cog, name="chatbot"):
    def __init__(self, bot):
        self.bot = bot
        self.chatlog_dir = CHATLOG_DIR
        self.channel_id = bot.channel_id
        self.chatbot = Chatbot("chardata.json", self.bot)

        # create chatlog directory if it doesn't exist
        if not os.path.exists(self.chatlog_dir):
            os.makedirs(self.chatlog_dir)

    # converts user ids and emoji ids
    async def replace_user_mentions(self, content):
        user_ids = re.findall(r'<@(\d+)>', content)
        for user_id in user_ids:
            user = await self.bot.fetch_user(int(user_id))
            if user:
                display_name = user.display_name
                content = content.replace(f"<@{user_id}>", display_name)

        emojis = re.findall(r'<:[^:]+:(\d+)>', content)
        for emoji_id in emojis:
            if ':' in content:
                emoji_name = content.split(':')[1]
                content = content.replace(f"<:{emoji_name}:{emoji_id}>", f":{emoji_name}:")
        return content




    @commands.command(name="batch_chat")
    async def batch_chat_command(self, message_content, channel) -> None:
        # get response message from chatbot and return it
        server_name = channel.id
        chatlog_filename = os.path.join(self.chatlog_dir, f"{server_name} - chatlog.txt")
        # set the conversation filename
        await self.chatbot.set_convo_filename(chatlog_filename)
        response = await self.chatbot.batch_save_conversation(message_content, channel)
        return response


async def setup(bot):
    # add chatbot cog to bot
    await bot.add_cog(ChatbotCog(bot))