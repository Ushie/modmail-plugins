from discord.ext import commands
from discord import Embed
from alpha_vantage.foreignexchange import ForeignExchange
from core import checks
from core.models import getLogger, PermissionLevel
from secrets import token_urlsafe

logger = getLogger(__name__)


class CurrencyConverter(commands.Cog):
    """Roles that are exclusive to people with certain roles only"""

    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    # @checks.has_permissions(PermissionLevel.REGULAR)
    async def convert(self, ctx, amount: float = 1, from_currency: str = "USD", to_currency: str = "USD"):
        # AlphaVantage has no API Key validation, any string that isn't "demo" will do
        apiKey = token_urlsafe(10)
        cc = ForeignExchange(key=apiKey)
        try:
            data, _ = cc.get_currency_exchange_rate(
                from_currency=from_currency, to_currency=to_currency)
            exchange_rate = float(data['5. Exchange Rate'])
            result = round(exchange_rate * amount, 3)
            embed = Embed(
                title="Currency Conversion Result",
                description=f'The conversion of {str(amount).rstrip("0").rstrip(".")} {from_currency} to {to_currency} is {str(result).rstrip("0").rstrip(".")}',
                color=self.bot.main_color,
            )
            embed.set_footer(
                text=f'Conversion Rate: 1 {from_currency} = {str(round(exchange_rate, 3)).rstrip("0").rstrip(".")} {to_currency}',
                icon_url=self.bot.get_guild_icon(guild=ctx.guild),
            )
        except ValueError as e:
            logger.debug(e)
            if "https://www.alphavantage.co/premium/" in str(e):
                embed = Embed(
                    title="API Call Limit Exceeded",
                    description="Apologies for the inconvenience. It seems that the maximum limit for API calls has been reached.",
                    color=self.bot.error_color,
                )
            elif "Invalid API call" in str(e):
                embed = Embed(
                    title="Invalid Currency Conversion Request",
                    description=f'The requested currency conversion from "{from_currency}" to "{to_currency}" is not valid. Please ensure that both source and target currencies are correctly specified using their respective currency codes.',
                    color=self.bot.error_color,
                )
            else:
                embed = Embed(
                    title="Unexpected Error",
                    description="An unexpected error occurred. Please open an issue at [GitHub](https://github.com/ushie/modmail-plugins) to report the problem.",
                    color=self.bot.error_color,
                )
            embed.set_footer(
                text=f'Please try again later',
                icon_url=self.bot.get_guild_icon(guild=ctx.guild),
            )
        await ctx.send(embed=embed)


async def setup(bot):
    await bot.add_cog(CurrencyConverter(bot))
