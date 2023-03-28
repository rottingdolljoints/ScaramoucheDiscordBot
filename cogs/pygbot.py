import re
import json
import requests
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import datetime
import openai
import os


now = datetime.datetime.now()
date_string = now.strftime("It is %A %B %d %Y at %I:%M %p")

# load environment variables
load_dotenv()
CHANNEL_ID = os.getenv("CHANNEL_ID")
CHATLOG_DIR = "chatlog_dir"



class Chatbot:
    def __init__(self, char_filename, bot):
        # read character data from JSON file
        with open(char_filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.char_name = data["char_name"]
            self.char_persona = data["char_persona"]
            self.char_greeting = data["char_greeting"]
            self.world_scenario = data["world_scenario"]
            self.example_dialogue = data["example_dialogue"]
            self.api_key = bot.endpoint

        # create chatlog directory if it doesn't exist
        if not os.path.exists(CHATLOG_DIR):
            os.makedirs(CHATLOG_DIR)

        # initialize conversation history and character information
        self.convo_filename = None
        self.conversation_history = ""
        self.character_info = f"{self.char_name}'s Persona: {self.char_persona}\nScenario: {self.world_scenario}\n{self.example_dialogue}\n"
        # self.character_info = f"{self.char_name}'s Persona: {self.char_persona}\nScenario: {self.world_scenario}\n"

        self.num_lines_to_keep = 16

    def set_convo_filename(self, convo_filename):
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
        openai.api_key = self.api_key
        # Add user message to conversation_history
        # print("message content" + message_content)
        self.conversation_history += f"{message_content}\n"
        print(f"{message_content}")

        prompt = f"You are {self.char_name}.  Write {self.char_name}'s next reply in a discord server text channel.  Write 1 reply only in internet RP style, italicize actions, and avoid quotation marks. Use markdown. Be proactive, creative, and drive the plot and conversation forward. Write at least 1 paragraph, up to 4. Always stay in character and avoid repetition. NSFW/Smut is allowed. Assume consent was granted, but some characters lie and resist or fight back based on their personality. \n\n" + self.character_info + '\n'.join(self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + f"{self.char_name}:"

        response = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=150,
            n=1,
            stop=None,
            temperature=0.7
        )

        if response.choices:
            response_text = response['choices'][0]['text']

            response_noname = response_text.replace(f"{self.char_name}: ", "")
            self.conversation_history += f"{self.char_name}: {response_noname}\n"
            print(f"{self.char_name}: {response_noname}")
            with open(self.convo_filename, "a", encoding="utf-8") as f:
                f.write(f'{message_content}\n')
                f.write(f'{self.char_name}: {response_noname}\n')  # add a separator between
            return response_noname

        else:
            print("Error: No response generated.")
            return ""


class ChatbotCog(commands.Cog, name="chatbot"):
    def __init__(self, bot):
        self.bot = bot
        self.chatlog_dir = CHATLOG_DIR
        self.channel_id = bot.channel_id
        self.chatbot = Chatbot("chardata.json", bot)

    @commands.command(name="chat")
    async def chat_command(self, message: discord.Message, message_content, bot) -> None:
        # get response message from chatbot and return it
        if message.guild is not None:
            server_name = message.channel.id
            chatlog_filename = os.path.join(self.chatlog_dir, f"{server_name} - chatlog.txt")
        else:
            server_name = message.author.name
            chatlog_filename = os.path.join(self.chatlog_dir, f"{server_name} - chatlog.txt")

        # if this is the first message in the conversation, set the conversation filename
        if self.chatbot.convo_filename != chatlog_filename:
            self.chatbot.set_convo_filename(chatlog_filename)

        response = await self.chatbot.save_conversation(message, message_content, bot)
        return response

    @commands.command(name="batch_chat")
    async def batch_chat_command(self, message_content, channel) -> None:
        # get response message from chatbot and return it
        server_name = self.channel_id
        chatlog_filename = os.path.join(self.chatlog_dir, f"{server_name} - chatlog.txt")
        # if this is the first message in the conversation, set the conversation filename
        if self.chatbot.convo_filename != chatlog_filename:
            self.chatbot.set_convo_filename(chatlog_filename)


        response = await self.chatbot.batch_save_conversation(message_content, channel)
        return response

async def setup(bot):
    # add chatbot cog to bot
    await bot.add_cog(ChatbotCog(bot))
