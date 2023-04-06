
import re
import json
import requests
import discord
from discord import app_commands
from discord.ext import commands
import os

import random
print("Debug: Pygbot initialized")
print("Debug: loading minilm")
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModel
from sentence_transformers import SentenceTransformer, util
import torch

def mean_pooling(model_output, attention_mask):
    token_embeddings = model_output[0] #First element of model_output contains all token embeddings
    input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
    return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)


from difflib import SequenceMatcher


with open("./chardata.json") as read_file:
    character_data = json.load(read_file)
    # Prompt the user to use the same character
    char_name = character_data['char_name']
    print('Debug: Character name is ' + char_name)

history = ''
currentthought = ""
# configuration settings for the api
model_config = {
    "use_story": False,
    "use_authors_note": False,
    "use_world_info": False,
    "use_memory": False,
    "max_context_length": 2400,
    "max_length": 32,
    "rep_pen": 1.02,
    "rep_pen_range": 1024,
    "rep_pen_slope": 0.9,
    "temperature": 0.8,
    "tfs": 0.9,
    "top_p": 0.9,
    "typical": 1,
    "sampler_order": [6, 0, 1, 2, 3, 4, 5]
}

smallermodel_config = {
    "use_story": False,
    "use_authors_note": False,
    "use_world_info": False,
    "use_memory": False,
    "max_context_length": 386,
    "max_length": 16,
    "rep_pen": 1.02,
    "rep_pen_range": 1024,
    "rep_pen_slope": 0.9,
    "temperature": 0.01,
    "tfs": 0.9,
    "top_p": 0.9,
    "typical": 1,
    "sampler_order": [6, 0, 1, 2, 3, 4, 5]
}

def is_similar(inp1, inp2, prefered_score=0.7):
    sentences = [inp1, inp2]
    print("Debug: Comparing " + str(inp1) + " and " + str(inp2))
    
    # If inp1 is not provided, return True
    if inp1 is None:
        print("Debug: inp1 is not provided")
        return True

    # Check if inp2 is a string or a list
    if isinstance(inp2, str):
        sentences.append(inp2)
    elif isinstance(inp2, list):
        sentences.extend(inp2)
    else:
        raise TypeError("inp2 must be a string or a list of strings")

    # Compute similarity score for all sentences
    score = 0
    for i in range(len(sentences)):
        for j in range(i+1, len(sentences)):
            s = SequenceMatcher(None, sentences[i], sentences[j]).ratio()
            if s > score:
                score = s

    if score >= prefered_score:
        print(f"Debug: {inp1} is similar to {inp2}")
        return True
    else:
        print(f"Debug: {inp1} is not similar to {inp2}")
        return False



def random_lines(text):
    print("Debug: Getting random lines")
    # Split the text into a list of lines delimited by "\n"
    lines = text.split("\n")
    # Remove any empty lines
    lines = [line for line in lines if line.strip()]
    print("Debug: There are " + str(len(lines)) + " lines")
    # Check if there are at least 5 non-empty lines
    if len(lines) < 5:
        # If there are fewer than 5 lines, return all the lines
        print("Debug: There are fewer than 5 lines")
        return lines
    else:
        # Otherwise, get 5 random lines from the list
        print("Debug: There are more than 5 lines")
        random_lines = random.sample(lines, 5)
        return random_lines



def concatenate_lines(lines):
    # Join the lines into a single string, separated by "\n"
    print("Debug: Concatenating lines")
    concatenated_lines = "\n".join(lines)
    return concatenated_lines






iteration = 0



hf_name = "C:\\Users\\admin\\Documents\\finetuned-bart-for-conversation-summary"

model = AutoModelForSeq2SeqLM.from_pretrained(
                hf_name,
                low_cpu_mem_usage=True,
            )

tokenizer = AutoTokenizer.from_pretrained(
                hf_name
            )


summarizer = pipeline(
                    "summarization",
                    model=model,
                    tokenizer=tokenizer
                )







def truncate_string(input_string,max_tokens=1024):
    print("Debug: Truncating string")
    tokenized_str = tokenizer.encode(input_string, add_special_tokens=False)
    print("Debug: Tokenized string is " + str(tokenized_str))
    # define the desired number of tokens
    num_tokens = max_tokens
    # slice the tokenized string based on the desired number of tokens
    sliced_tokens = tokenized_str[:num_tokens]

    # decode the sliced tokens to get the sliced string
    sliced_str = tokenizer.decode(sliced_tokens)
    print("Debug: Truncated string is " + sliced_str)
    return(sliced_str)


def summarize_string(input_string):
    # truncate the input to a maximum of 1024 tokens
    input_string = truncate_string(input_string,1024)
    print("Debug: Summarizing string")
    summarized = summarizer(
           truncate_string(input_string,1024),
           min_length=16,
           max_length=1024,
           no_repeat_ngram_size=3,
           encoder_no_repeat_ngram_size =3,
           clean_up_tokenization_spaces=True,
           repetition_penalty=3.7,
           num_beams=4,
           early_stopping=True,
    )

    print("Debug: Summarized string is " + summarized[0]["summary_text"])
    return summarized[0]["summary_text"]

def writememory(input_String):
    if input_String not in readmemory():
        with open("memory.txt", "a") as f:
                f.write(summarize_string(input_String) + "\n")
        f.close()



def readmemory(inp1 = ""):

    temp =  open("memory.txt","r").read()

    temp2 = temp.split("\n")
    print("Memories:\n\n\n\n")
    print(temp2)
    print("\n\n\n\n")
    temp_list = []
    if inp1 != "":
        for x in range(0, len(temp2)):
            if is_similar(temp2[x],inp1):
                temp_list.append(temp2[x])

        return concatenate_lines(temp_list)
    else:
        return concatenate_lines(random_lines(temp))

def writememory(input_String):
    if input_String not in readmemory():
        with open("memory.txt", "a") as f:
                f.write(summarize_string(input_String))
                f.write("\n")
        f.close()



def attention_check(chat,character_info,char_name):
    global currentthought
    current_memory = readmemory()
    print("Debug: Writing to memory")
    current_memory = current_memory + "\nmy name is " + char_name + " and I only respond to messages directed to me.\n"
    prompt = {
    "prompt":
    character_info + '\n' + readmemory() + "\nBelow is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.\n\n### Instruction:\ncontinue this conversation accurately:\n\n### Input:\n" +  '\n'.join(
                chat.split("\n")),
        }
    print("Debug: Prompt is " + prompt["prompt"])
    # send a post request to the API endpoint
    requests.put("http://127.0.0.1:5000/api/v1/config", json=smallermodel_config)
    response = requests.post("http://127.0.0.1:5000/api/v1/generate", json=prompt)
    # check if the request was successful
    if response.status_code == 200:
        # Get the results from the response
        results = response.json()['results']
        response_list = [line for line in results[0]['text'][1:].split("\n")]
        result = [response_list[0]]
        for item in response_list[1:]:
            if char_name in item:
                result.append(item)
            else:
                break
        print("Potential conversation outcome:\n\n")
        print(results[0]["text"])
        global currentthought
        requests.put("http://127.0.0.1:5000/api/v1/config", json=model_config)
        
        tempresult = results[0]["text"]
        tempresult = tempresult.lower()
        # tempresult = tempresult.replace("rtifex",f"{self.char_name}")
        # tempresult = tempresult.replace("artifex",f"{self.char_name}")
        # tempresult = tempresult.replace("rtifice",f"{self.char_name}")
        tempresult = tempresult.replace(f"{char_name}"[1:],f"{char_name}")
        tempresult = tempresult.replace(f"{char_name}"[:1],f"{char_name}")
        tempresult = tempresult.replace("you",f"{char_name}")
        tempresult = tempresult.replace("bot",f"{char_name}")
        templist = tempresult.split(' ')
        print("Debug: Templist is")
        print(templist)


        replies = results[0]["text"].split('\n')
        print("Debug: Replies are")
        verdict = False
        for x in range(0,len(templist)):
            if is_similar(f"{char_name}".lower(),templist[x]):
                verdict = True
                print("Debug: I choose to reply")
                print(replies[0])
                currentthought = f"{char_name}'s current thought:" + replies[0].replace(f"{char_name}:","")
                break


        return verdict



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


        # initialize conversation history and character information
        self.convo_filename = None
        global history
        self.conversation_history = ""
        history = self.conversation_history
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

    async def save_conversation(self, message, message_content):
        print("Debug: Conversation saved")
        self.conversation_history += f'{message.author.name}: {message_content}\n'
        global iteration
        global currentthought
        iteration += 1
        message_content = truncate_string(message_content,512)
        self.prompt = {
            "prompt": self.character_info + '\n' + readmemory(message_content) + '\n'.join(
                self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + currentthought  + '\n' +  f'{self.char_name}:',
        }

        # send a post request to the API endpoint
        charinfo = f'{{"char_name":"{self.char_name}","char_persona":"{self.char_persona}","char_greeting":"{self.char_greeting}","world_scenario":"","example_dialogue":""}}'
        verdict = attention_check(self.conversation_history,charinfo,f"{self.char_name}")
        if verdict == True:
            response = requests.post(f"{self.endpoint}/api/v1/generate", json=self.prompt)
        else:
            response = requests.Response()
            response.status_code = 422
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
            # add bot response to conversation history
            self.conversation_history = self.conversation_history + f'{self.char_name}: {response_text}\n'
            with open(self.convo_filename, "a", encoding="utf-8") as f:
                f.write(f'{message.author.name}: {message_content}\n')
                f.write(f'{self.char_name}: {response_text}\n')  # add a separator between
                            # define the prompt
            if iteration >= 5:
                print(self.conversation_history)
                print('\n\n\n')
                print(summarize_string(self.conversation_history))
                self.conversation_history.replace(self.conversation_history,"\n")
                writememory(summarize_string(self.conversation_history))
                writememory("\n")
                iteration = 0

            global history
            history = self.conversation_history
            return response_text

    async def follow_up(self):
        message_content = truncate_string(message_content,512)
        self.prompt = {
            "prompt": self.character_info + '\n' + readmemory(message_content) + '\n'.join(
                self.conversation_history.split('\n')[-self.num_lines_to_keep:]) + currentthought  + '\n' +  f'{self.char_name}:',
        }

        print(self.prompt)
        charinfo = f'{"char_name":"{self.char_name}","char_persona":"{self.char_name} is an artificial intelligence assistant made by the face of goonery. {self.char_name} is a creative, confident and smart person, and will accept correction and never lie.","char_greeting":"Sup","world_scenario":"","example_dialogue":""}'
        verdict = attention_check(self.conversation_history,charinfo,f"{self.char_name}")
        if verdict == True:
            response = requests.post(f"{self.endpoint}/api/v1/generate", json=self.prompt)
        else:
            response = ""
            response.status_code = 422
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
            global history
            history = self.conversation_history
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

        # Get the gnarly response message from the chatbot and return it, dude!
        if message.guild:
            server_name = message.channel.name
        else:
            server_name = message.author.name
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
        charinfo = f'{"char_name":"{self.char_name}","char_persona":"{self.char_name} is an artificial intelligence assistant made by the face of goonery. {self.char_name} is a creative, confident and smart person, and will accept correction and never lie.","char_greeting":"Sup","world_scenario":"","example_dialogue":""}'
        verdict = attention_check(history,charinfo,f"{self.char_name}")
        if verdict == True:
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
                    if lines[i].startswith(f"{self.bot.name}:"):
                        lines[i] = f"{self.bot.name}:"
                        self.chatbot.conversation_history = "\n".join(lines)
                        self.chatbot.conversation_history = self.chatbot.conversation_history
                        break
                print(f"string after: {repr(self.chatbot.conversation_history)}")
                break  # Exit the loop after deleting the message
        with open(self.chatbot.convo_filename, "r", encoding="utf-8") as f:
            lines = f.readlines()
            # Find the last line that matches "Tensor: {message.content}"
            last_line_num_to_overwrite = None
            for i in range(len(lines) - 1, -1, -1):
                if f"{self.bot.name}: {message.content}" in lines[i]:
                    last_line_num_to_overwrite = i
                    break
            if last_line_num_to_overwrite is not None:
                lines[last_line_num_to_overwrite] = ""
                # Modify the last line that matches "self.bot.name: {message.content}"
            with open(self.chatbot.convo_filename, "w", encoding="utf-8") as f:
                f.writelines(lines)
                f.close()

        global history

        charinfo = f'{"char_name":"{self.char_name}","char_persona":f"{self.char_name} is an artificial intelligence assistant made by the face of goonery. {self.char_name} is a creative, confident and smart person, and will accept correction and never lie.","char_greeting":"Sup","world_scenario":"","example_dialogue":""}'
        verdict = attention_check(history,charinfo,f"{self.char_name}")
        if verdict == True:
            await interaction.channel.send(await self.chatbot.follow_up())




async def setup(bot):
    # add chatbot cog to bot
    await bot.add_cog(ChatbotCog(bot))
