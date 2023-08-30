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
    @checks.has_permissions(PermissionLevel.REGULAR)
    async def convert(
        self,
        ctx,
        amount: float = 1,
        from_currency: str = "USD",
        to_currency: str = "USD",
    ):
        def get_exchange_rate(from_currency, to_currency):
            apiKey = token_urlsafe(10)  # AlphaVantage has no API Key validation
            cc = ForeignExchange(key=apiKey)
            data, _ = cc.get_currency_exchange_rate(
                from_currency=from_currency, to_currency=to_currency
            )
            return {
                "exchange_rate": float(data["5. Exchange Rate"]),
                "from_currency": from_currency,
                "to_currency": to_currency,
            }

        def handle_api_call(exchange_data):
            match exchange_data["exchange_rate"]:
                case None:
                    logger.debug("API call limit exceeded")
                    embed = Embed(
                        title="API Call Limit Exceeded",
                        description="Apologies for the inconvenience. It seems that the maximum limit for API calls has been reached.",
                        color=self.bot.error_color,
                    )
                    embed.set_footer(
                        text=f"Please try again later",
                        icon_url=self.bot.get_guild_icon(guild=ctx.guild),
                    )
                case "Invalid API call":
                    logger.debug("Invalid API call")
                    embed = Embed(
                        title="Invalid Currency Conversion Request",
                        description=f'The requested currency conversion from "{exchange_data["from_currency"].upper()}" to "{exchange_data["to_currency"].upper()}" is not valid. Please ensure that both source and target currencies are correctly specified using their respective currency codes.',
                        color=self.bot.error_color,
                    )
                    embed.set_footer(
                        text=f"Please try again later",
                        icon_url=self.bot.get_guild_icon(guild=ctx.guild),
                    )
                case float(_):
                    result = round(exchange_data["exchange_rate"] * amount, 3)
                    embed = Embed(
                        title="Currency Conversion Result",
                        description=f'The conversion of {amount:g} {exchange_data["from_currency"].upper()} to {exchange_data["to_currency"].upper()} is {result:g}',
                        color=self.bot.main_color,
                    )
                    embed.set_footer(
                        text=f'Conversion Rate: 1 {exchange_data["from_currency"].upper()} = {round(exchange_data["exchange_rate"], 3):g} {exchange_data["to_currency"].upper()}',
                        icon_url=self.bot.get_guild_icon(guild=ctx.guild),
                    )
                case _:
                    logger.debug("Unexpected error")
                    embed = Embed(
                        title="Unexpected Error",
                        description="An unexpected error occurred. Please open an issue at [GitHub](https://github.com/ushie/modmail-plugins) to report the problem.",
                        color=self.bot.error_color,
                    )
                    embed.set_footer(
                        text=f"Please try again later",
                        icon_url=self.bot.get_guild_icon(guild=ctx.guild),
                    )
            return embed

        await ctx.send(
            embed=handle_api_call(get_exchange_rate(from_currency, to_currency))
        )


async def setup(bot):
    await bot.add_cog(CurrencyConverter(bot))
