import discord
from discord.ext import commands
from PIL import Image
from io import BytesIO
import requests
import re
import torch
from transformers import AutoProcessor, AutoModelForCausalLM



class ImageCaptionCog(commands.Cog, name="image_caption"):
    def __init__(self, bot):
        self.bot = bot
        self.processor = AutoProcessor.from_pretrained("C:\\Users\\admin\\Documents\\git-base-coco")
        self.model = AutoModelForCausalLM.from_pretrained("C:\\Users\\admin\\Documents\\git-base-coco",
                                                                  torch_dtype=torch.float32).to("cpu")

    @commands.command(name="image_comment")
    async def image_comment(self, message: discord.Message, message_content) -> None:
        # Check if the message content is a URL
        url_pattern = re.compile(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+')
        if "https://tenor.com/view/" in message_content:
            # Extract the Tenor GIF URL from the message content
            start_index = message_content.index("https://tenor.com/view/")
            end_index = message_content.find(" ", start_index)
            if end_index == -1:
                tenor_url = message_content[start_index:]
            else:
                tenor_url = message_content[start_index:end_index]
            # Split the URL on forward slashes
            parts = tenor_url.split("/")
            # Extract the relevant words from the URL
            words = parts[-1].split("-")[:-1]
            # Join the words into a sentence
            sentence = " ".join(words)
            message_content = f"{message_content} [{message.author.name} posts an animated {sentence} ]"
            message_content = message_content.replace(tenor_url, "")
            return message_content

        elif url_pattern.match(message_content):
            # Download the image from the URL and convert it to a PIL image
            response = requests.get(message_content)
            image = Image.open(BytesIO(response.content)).convert('RGB')
        else:
            # Download the image from the message and convert it to a PIL image
            image_url = message.attachments[0].url
            response = requests.get(image_url)
            image = Image.open(BytesIO(response.content)).convert('RGB')

        # Generate the image caption
        caption = self.caption_image(image,message_content)
        message_content = f"{message_content} [{message.author.name} posts a picture. {caption}]"
        return message_content

    def caption_image(self, raw_image,question=""):
        pixel_values = processor(images=raw_image, return_tensors="pt").pixel_values

        generated_ids = model.generate(pixel_values=pixel_values, max_length=150)
        generated_caption = processor.batch_decode(generated_ids, skip_special_tokens=True)[0]

        #inputs = self.processor(raw_image.convert('RGB'), return_tensors="pt").to("cpu", torch.float32)
        #out = self.model.generate(**inputs, max_new_tokens=50)
        #caption = self.processor.decode(out[0], skip_special_tokens=True)

        #return caption
        print(generated_caption)
        return question + ". It's a picture of " + str(generated_caption)


async def setup(bot):
    await bot.add_cog(ImageCaptionCog(bot))