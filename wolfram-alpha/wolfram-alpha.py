import discord
from discord.ext import commands
from urllib.parse import quote as escape
import aiohttp
import json

wolfram_icon = 'https://i.imgur.com/sGKq1A6.png'
wolfram_url = 'http://www.wolframalpha.com/input/?i='
api_url = 'http://api.wolframalpha.com/v2/query?output=JSON&format=image,plaintext&input='


class SubPod(object):
    def __init__(self, data):
        self.text = data.get('plaintext', '').strip()
        self.image = data.get('img', {}).get('src') or None


class Pod(object):
    def __init__(self, data):
        self.title = data.get('title', '').strip()
        self.subpods = [SubPod(p) for p in data.get('subpods')]
        self.is_primary = data.get('primary')


class WolframResult(object):
    def __init__(self, data):
        self.pods = [Pod(p) for p in data.get('pods', [])]
        self.primary_pod = next((p for p in self.pods if p.is_primary), None)
        self.success = data.get('success') and bool(self.primary_pod)


class WolframCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.plugin_db.get_partition(self)
        self.allowed_mentions = discord.AllowedMentions.none()
        self.app_id = None
        self.bot.loop.create_task(self._set_db())

    async def _set_db(self):
        data = await self.db.find_one({"_id": "wolfram"})
        if data is None:
            await self.db.insert_one({"_id": "wolfram", "app_id": None})
            data = {"app_id": None}

        self.app_id = data["app_id"]

    async def aioget(self, url, as_json=False):
        async with aiohttp.ClientSession() as aio_client:
            async with aio_client.get(url) as aio_session:
                response = await aio_session.text()
                if as_json:
                    response = json.loads(response)
        return response

    async def send_response(self, message, init, response):
        if init:
            await init.edit(embed=response)
        else:
            await message.channel.send(embed=response)

    async def wolframalpha(self, ctx, *args):
        if not args:
            response = discord.Embed(
                color=0xBE1931,
                title='🔍 Nothing inputted.'
            )
            await ctx.send(embed=response)
            return

        full_results = False
        if args and args[-1].lower() == '--full':
            args = args[:-1]
            full_results = True

        query = self.make_safe_query(args)
        url = f'{api_url}{query}&appid={self.app_id}'
        init_response = discord.Embed(color=0xff7e00)
        init_response.set_author(name='Processing request...', icon_url=wolfram_icon)
        init_message = await ctx.send(embed=init_response)
        results = await self.aioget(url, as_json=True)
        results = WolframResult(results.get('queryresult'))
        if not results.success:
            response = discord.Embed(
                color=0x696969,
                title='🔍 No results.'
            )
            await self.send_response(ctx.message, init_message, response)
            return

        try:
            response = discord.Embed(color=0xff7e00)
            response.set_author(name='Wolfram|Alpha', icon_url=wolfram_icon, url=wolfram_url + query)
            if not full_results:
                subpod = results.primary_pod.subpods[0]
                if subpod.text:
                    response.description = f'```\n{subpod.text}\n```'
                else:
                    response.set_image(url=subpod.image)
                response.set_footer(text='Add "--full" to the end to see the full result.')
                await self.send_response(ctx.message, init_message, response)
                return

            image_set = False
            for i, pod in enumerate(results.pods):
                values = []
                for subpod in pod.subpods:
                    if subpod.text:
                        values.append(f'```\n{subpod.text}\n```')
                    elif subpod.image:
                        if not image_set:
                            values.append('(See embedded image)')
                            response.set_image(url=subpod.image)
                            image_set = True
                        else:
                            values.append(f'[Click to view image]({subpod.image})')
                if values:
                    values = '\n'.join(values)
                    response.add_field(name=f'{i + 1}. {pod.title}', value=values, inline=False)
            response.set_footer(text='View the results online by clicking the embed title.')
            await self.send_response(ctx.message, init_message, response)

        except discord.HTTPException:
            response = discord.Embed(
                color=0xBE1931,
                title='❗ Results too long to display.'
            )
            response.description = f'You can view them directly [here]({wolfram_url + query}).'
            await self.send_response(ctx.message, init_message, response)

    def make_safe_query(self, query):
        safe = r'`~!@$^*()[]{}\|:;"\'<>,.'
        safe_query = ''.join(escape(char, safe=safe) for char in ' '.join(query).lower())
        return safe_query

    @commands.command()
    async def wolfram(self, ctx, *args):
        await self.wolframalpha(ctx, *args)

    @commands.group()
    async def wolframconfig(self, ctx):
        """
        Subcommand group for configuring Wolfram|Alpha app ID.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @wolframconfig.command(name="setappid")
    async def set_app_id(self, ctx, app_id: str):
        """
        Set the Wolfram|Alpha app ID.
        """
        await self.db.find_one_and_update(
            {"_id": "wolfram"},
            {"$set": {"app_id": app_id}},
            upsert=True
        )
        self.app_id = app_id
        await ctx.send("Wolfram|Alpha app ID set successfully.")


async def setup(bot):
    await bot.add_cog(WolframCog(bot))
