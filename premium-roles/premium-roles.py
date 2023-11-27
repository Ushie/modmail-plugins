import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel

class PremiumRoles(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.db = bot.plugin_db.get_partition(self)
        self.required_roles = []
        self.premium_roles = []
        self.allowed_mentions = discord.AllowedMentions(roles=False, users=False, everyone=False)
        self.bot.loop.create_task(self._set_db())

    async def _set_db(self):
        data = await self.db.find_one({"_id": "premium_roles"})
        if data is None:
            await self.db.insert_one({"_id": "premium_roles", "required_roles": [], "premium_roles": []})
            data = {"required_roles": [], "premium_roles": []}

        self.required_roles = data["required_roles"]
        self.premium_roles = data["premium_roles"]

    async def _update_db(self):
        await self.db.find_one_and_update(
            {"_id": "premium_roles"},
            {"$set": {"required_roles": self.required_roles, "premium_roles": self.premium_roles}},
            upsert=True
        )

    @commands.group(invoke_without_command=True)
    async def premium(self, ctx):
        """
        Base command for managing premium roles.
        """
        await ctx.send_help(ctx.command)

    @premium.group(name="config")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config(self, ctx):
        """
        Subcommand group for configuring premium roles.
        """
        if ctx.invoked_subcommand is None:
            await ctx.send_help(ctx.command)

    @premium_config.command(name="get")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_get(self, ctx):
        """
        Get existing premium and required roles.
        """
        required_role_mentions = [ctx.guild.get_role(role_id).mention for role_id in self.required_roles]
        premium_role_mentions = [ctx.guild.get_role(role_id).mention for role_id in self.premium_roles]

        required_roles_str = "\n".join(required_role_mentions) if required_role_mentions else "None"
        premium_roles_str = "\n".join(premium_role_mentions) if premium_role_mentions else "None"

        response = f"Required Roles:\n{required_roles_str}\n\nPremium Roles:\n{premium_roles_str}"
        await ctx.send(response, allowed_mentions=self.allowed_mentions)
    
    @premium_config.command(name="addrequired")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_add_required(self, ctx, role: discord.Role):
        """
        Add required role.
        """
        self.required_roles.append(role.id)
        await self._update_db()
        await ctx.send(f"Added {role.mention} as a required role!", allowed_mentions=self.allowed_mentions)

    @premium_config.command(name="removerequired")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_remove_required(self, ctx, role: discord.Role):
        """
        Remove required role.
        """
        if role.id in self.required_roles:
            self.required_roles.remove(role.id)
            await self._update_db()
            await ctx.send(f"Removed {role.mention} from required roles.", allowed_mentions=self.allowed_mentions)
        else:
            await ctx.send(f"{role.mention} is not in the required roles list.", allowed_mentions=self.allowed_mentions)

    @premium_config.command(name="add")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_add_premium(self, ctx, role: discord.Role):
        """
        Add premium role.
        """
        self.premium_roles.append(role.id)
        await self._update_db()
        await ctx.send(f"Added {role.mention} as a premium role!", allowed_mentions=self.allowed_mentions)

    @premium_config.command(name="remove")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_remove_premium(self, ctx, role: discord.Role):
        """
        Remove premium role.
        """
        if role.id in self.premium_roles:
            self.premium_roles.remove(role.id)
            await self._update_db()
            await ctx.send(f"Removed {role.mention} from premium roles.", allowed_mentions=self.allowed_mentions)
        else:
            await ctx.send(f"{role.mention} is not in the premium roles list.", allowed_mentions=self.allowed_mentions)

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Check if the roles of the member have changed
        if before.roles == after.roles:
            return
        
        if not self.required_roles:
            return

        # Determine if the member has any required roles
        has_required_role = any(role.id in self.required_roles for role in after.roles)

        # Remove premium roles if necessary
        roles_to_remove = [role for role in after.roles if role.id in self.premium_roles]
        if not has_required_role and roles_to_remove:
            await after.remove_roles(*roles_to_remove)

async def setup(bot):
    await bot.add_cog(PremiumRoles(bot))
