import re
import json
import requests
import discord
from discord import app_commands
from discord.ext import commands
from langchain.chains import ConversationChain
import os
from cleantext import clean
from langchain import KoboldApiLLM
from langchain.prompts.prompt import PromptTemplate

def embedder(msg):
    embed = discord.Embed(
            description=f"{msg}",
            color=0x9C84EF
        )
    return embed



class Chatbot:
    def __init__(self, char_filename, bot):
        self.prompt = None
        self.endpoint = bot.endpoint
        self.histories = {}  # Initialize the history dictionary
        self.stop_sequences = {}  # Initialize the stop sequences dictionary
        self.llm = KoboldApiLLM(endpoint=self.endpoint)

        with open(char_filename, "r", encoding="utf-8") as f:
            data = json.load(f)
            self.char_name = data.get("char_name", "")
            self.char_persona = data.get("char_persona", "")
            self.world_scenario = data.get("world_scenario", "")
            self.example_dialogue = data.get("example_dialogue", "")

        # initialize conversation history and character information
        self.convo_filename = None
        self.conversation_history = ""
        self.top_character_info = self.format_character_info()
        self.bottom_character_info = self.format_bottom_character_info()
        """
        
        the format I want:
        Persona : top character info
        Scenario : top character info
        Example of Dialogues : top character info
        Chat history
        Author's Note aka bottom character info
        User message : name: message_content
        Bot Name:
        """
        
        
    def format_bottom_character_info(self):
        """
        This helper function formats the character_info string, including the optional parts only if they exist.
        """
        info_str = f"\n{self.char_name}'s Persona: {self.char_persona}\n"

        if self.world_scenario:
            info_str += f"\nScenario: {self.world_scenario}\n"
            
        return info_str
        

        
        
    def format_top_character_info(self):
        """
        This helper function formats the character_info string, including the optional parts only if they exist.
        """
        info_str = f"Character: {self.char_name}\n{self.char_name}'s Persona: {self.char_persona}\n"

        if self.world_scenario:  # Check if world_scenario exists
            info_str += f"Scenario: {self.world_scenario}\n"
        
        if self.example_dialogue:  # Check if example_dialogue exists
            info_str += f"Example Dialogue:\n{self.example_dialogue}\n"
            
        return info_str

    async def get_stop_sequence_for_channel(self, channel_id, name):
        name_token = f"\n{name}:"
        if channel_id not in self.stop_sequences:
            self.stop_sequences[channel_id] = [
                "### Instruction",
                "### Response",
                "\n\n"
            ] 
        if name_token not in self.stop_sequences[channel_id]:
            self.stop_sequences[channel_id].append(name_token)
        return self.stop_sequences[channel_id]

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

    async def generate_response(self, message, message_content) -> None:
        channel_id = str(message.channel.id)
        name = message.author.display_name
        memory = await self.get_memory_for_channel(str(channel_id))
        stop_sequence = await self.get_stop_sequence_for_channel(channel_id, name)
        chat_participants = await self.get_chat_participants_for_channel(channel_id, name)
        print(f"chat participants: {chat_participants}\n total chat participants: {len(chat_participants)}")
        print(f"stop sequences: {stop_sequence}")
        formatted_message = f"{name}: {message_content}"
        system_message = await self.generate_system_message()
        MAIN_TEMPLATE = '''
{{history}}
{{input}}
{BOTNAME}:'''
        
        
        PROMPT = PromptTemplate(
            input_variables=["history", "input", "bot_name",""], template=MAIN_TEMPLATE
        )
        
        
        # Create a conversation chain using the channel-specific memory
        conversation = ConversationChain(
            prompt=PROMPT,
            llm=self.llm,
            verbose=True,
            memory=memory,
        )
        input_dict = {"input": formatted_message, "stop": stop_sequence}
        response_text = conversation(input_dict)
        response = await self.detect_and_replace_out(response_text["response"])
        with open(self.convo_filename, "a", encoding="utf-8") as f:
            f.write(f'{message.author.display_name}: {message_content}\n')
            f.write(f'{self.char_name}: {response_text}\n')  # add a separator between

        return response
            

    async def save_conversation(self, message, message_content):
        channel_id = str(message.channel.id)
        self.conversation_history += f'{message.author.display_name}: {message_content}\n'
        stop_sequence = await self.get_stop_sequence_for_channel(channel_id, self.char_name)
        # create a multiline fstring version of self.character_info
        
        self.character_info = """
        {self.char_name}'s Persona: {self.char_persona}
        Scenario: {self.world_scenario}
        
        """
        # define the prompt
        self.prompt =  self.character_info + '\n'.join(self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + f'{self.char_name}:'
        


        # send a post request to the API endpoint
        response = self.llm(self.prompt, stop_sequences=stop_sequence) 
        # check if the request was successful

        # add bot response to conversation history
        self.conversation_history = self.conversation_history + f'{self.char_name}: {response}\n'
        with open(self.convo_filename, "a", encoding="utf-8") as f:
            f.write(f'{message.author.display_name}: {message_content}\n')
            f.write(f'{self.char_name}: {response}\n')  # add a separator between

            return response

    async def follow_up(self):
        self.conversation_history = self.conversation_history
        self.prompt = {
            "prompt": self.character_info + '\n'.join(
                self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + f"{self.char_name}:",
        }
        print(self.prompt)
        response = requests.post(f"{self.endpoint}/api/v1/generate", json=self.prompt)
        print(response.json()['results'])
        # check if the request was successful
        if response.status_code == 200:
            # Get the results from the response
            results = response.json()['results']
            response_list = [line for line in results[0]['text'][1:].split("\n")]
            result = [response_list[0]]
            for item in response_list[1:]:
                if self.char_name in item:
                    result.append(item)
                else:
                    break
            new_list = [item.replace(self.char_name + ": ", '\n') for item in result]
            response_text = ''.join(new_list)
            self.conversation_history = self.conversation_history + f'{self.char_name}: {response_text}\n'
            with open(self.convo_filename, "a", encoding="utf-8") as f:
                f.write(f'{self.char_name}: {response_text}\n')  # add a separator between
            return response_text



class ChatbotCog(commands.Cog, name="chatbot"):
    def __init__(self, bot):
        self.bot = bot
        self.chatlog_dir = bot.chatlog_dir
        self.chatbot = Chatbot("chardata.json", bot)

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



    # Normal Chat handler
    @commands.command(name="chat")
    async def chat_command(self, message, message_content) -> None:
        if message.guild:
            server_name = message.channel.name
        else:
            server_name = message.author.display_name
        chatlog_filename = os.path.join(self.chatlog_dir, f"{self.chatbot.char_name}_{server_name}_chatlog.log")
        if message.guild and self.chatbot.convo_filename != chatlog_filename or \
                not message.guild and self.chatbot.convo_filename != chatlog_filename:
            await self.chatbot.set_convo_filename(chatlog_filename)
        response = await self.chatbot.save_conversation(message, await self.replace_user_mentions(message_content))
        return response

    @app_commands.command(name="followup", description="Make the bot send another message")
    async def followup(self, interaction: discord.Interaction) -> None:
        if interaction.guild:
            server_name = interaction.channel.name
        else:
            server_name = interaction.author.name
        chatlog_filename = os.path.join(self.chatlog_dir, f"{self.chatbot.char_name}_{server_name}_chatlog.log")
        if interaction.guild and self.chatbot.convo_filename != chatlog_filename or \
                not interaction.guild and self.chatbot.convo_filename != chatlog_filename:
            await self.chatbot.set_convo_filename(chatlog_filename)
        await interaction.response.defer()
        await interaction.delete_original_response()
        await interaction.channel.send(await self.chatbot.follow_up())




    @app_commands.command(name="regenerate", description="regenerate last message")
    async def regenerate(self, interaction: discord.Interaction) -> None:
        await interaction.response.defer()
        await interaction.delete_original_response()
        if interaction.guild:
            server_name = interaction.channel.name
        else:
            server_name = interaction.author.name
        chatlog_filename = os.path.join(self.chatlog_dir, f"{self.chatbot.char_name}_{server_name}_chatlog.log")
        if interaction.guild and self.chatbot.convo_filename != chatlog_filename or \
                not interaction.guild and self.chatbot.convo_filename != chatlog_filename:
            await self.chatbot.set_convo_filename(chatlog_filename)
        # Get the last message sent by the bot in the channel
        async for message in interaction.channel.history(limit=1):
            if message.author == self.bot.user:
                await message.delete()
                lines = self.chatbot.conversation_history.splitlines()
                for i in range(len(lines) - 1, -1, -1):
                    if lines[i].startswith(f"{self.chatbot.char_name}:"):
                        lines[i] = f"{self.chatbot.char_name}:"
                        self.chatbot.conversation_history = "\n".join(lines)
                        self.chatbot.conversation_history = self.chatbot.conversation_history
                        break
                print(f"string after: {repr(self.chatbot.conversation_history)}")
                break  # Exit the loop after deleting the message
        with open(self.chatbot.convo_filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Find the last line that matches "self.chatbot.char_name: {message.content}"
            last_line_num_to_overwrite = None
            for i in range(len(lines) - 1, -1, -1):
                if f"{self.chatbot.char_name}: {message.content}" in lines[i]:
                    last_line_num_to_overwrite = i
                    break
            if last_line_num_to_overwrite is not None:
                lines[last_line_num_to_overwrite] = ""
                # Modify the last line that matches "self.chatbot.char_name: {message.content}"
            with open(self.chatbot.convo_filename, "w", encoding="utf-8") as f:
                f.writelines(lines)
                f.close()
        await interaction.channel.send(await self.chatbot.follow_up())

        
    async def api_get(self, parameter):
        response = requests.get(f"{self.chatbot.endpoint}/api/v1/config/{parameter}")
        return response.json()

    async def api_put(self, parameter, value):
        response = requests.put(f"{self.chatbot.endpoint}/api/v1/config/{parameter}", json={"value": value})
        return response.json()

    @app_commands.command(name="koboldget", description="Get the value of a parameter from the API")
    async def koboldget(self, interaction: discord.Interaction, parameter: str):
        try:
            value = await self.api_get(parameter)
            print(f"Parameter '{parameter}' value: {value}")
            await interaction.response.send_message(embed=embedder(f"Parameter {parameter} value: {value}"),
                                                    delete_after=3)
        except Exception as e:
            await interaction.response.send_message(embed=embedder(f"Error: {e}"), delete_after=12)

    @app_commands.command(name="koboldput", description="Set the value of a parameter in the API")
    async def koboldput(self, interaction: discord.Interaction, parameter: str, value: str):
        try:
            result = await self.api_put(parameter, value)
            await interaction.response.send_message(embed=embedder(f"Parameter '{parameter}' updated to: {value}"),
                                                    delete_after=3)
        except Exception as e:
            await interaction.response.send_message(embed=embedder(f"Error: {e}"), delete_after=12)




async def setup(bot):
    # add chatbot cog to bot
    await bot.add_cog(ChatbotCog(bot))