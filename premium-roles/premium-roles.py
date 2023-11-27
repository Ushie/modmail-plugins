import discord
from discord.ext import commands
from core import checks
from core.models import PermissionLevel


async def remove_roles_if_necessary(member, required_roles, premium_roles):
    has_required_role = any(role.id in required_roles for role in member.roles)
    roles_to_remove = [role for role in member.roles if role.id in premium_roles]
    if not has_required_role and roles_to_remove:
        await member.remove_roles(*roles_to_remove)
        return True  # Indicate that roles were removed for this member
    return False  # Indicate that no roles were removed for this member


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

    @premium.command(name="purge")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def purge_users(self, ctx):
        """
        Check all members with premium roles and revoke if ineligible.
        """
        removed_count = 0
        for role_id in self.premium_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                for member in role.members:
                    if await remove_roles_if_necessary(member, self.required_roles, member.roles):
                        removed_count += 1
            else:
                print(f"Role {role_id} not found.")

        await ctx.send(f"Roles removed for {removed_count} member(s).", allowed_mentions=self.allowed_mentions)

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
        roles_info = {
            "Required Roles": {"Valid": [], "Invalid": []},
            "Premium Roles": {"Valid": [], "Invalid": []}
        }

        for role_id in self.required_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_info["Required Roles"]["Valid"].append(role.mention)
            else:
                roles_info["Required Roles"]["Invalid"].append(role_id)

        for role_id in self.premium_roles:
            role = ctx.guild.get_role(role_id)
            if role:
                roles_info["Premium Roles"]["Valid"].append(role.mention)
            else:
                roles_info["Premium Roles"]["Invalid"].append(role_id)

        response = ''
        for role_type, status in roles_info.items():
            response += f"{role_type}:\n- "
            response += "\n- ".join(status["Valid"]) if status["Valid"] else "None"
            response += "\n\n"

        invalid_roles = [(role_id, role_type) for role_type, status in roles_info.items() if role_type != "Valid" for
                         role_id in status["Invalid"]]

        if invalid_roles:
            response += f"Invalid roles:"
            for role_type in ("Premium Roles", "Required Roles"):
                role_invalid_list = [f"    - {role_id}" for role_id, rt in
                                     invalid_roles if rt == role_type]
                if role_invalid_list:
                    response += f"\n- {role_type}:\n"
                    response += "\n".join(role_invalid_list)
            response += "\nYou can remove the invalid roles with the `premium config removeinvalid` command"
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

    @premium_config.command(name="removeinvalid")
    @checks.has_permissions(PermissionLevel.ADMINISTRATOR)
    async def premium_config_remove_invalid(self, ctx):
        """
        Remove invalid roles.
        """
        roles_removed = 0

        async def remove_invalid_roles(role_ids):
            count = 0
            for role_id in role_ids:
                role = ctx.guild.get_role(role_id)
                if not role:
                    self.premium_roles.remove(role_id)
                    await self._update_db()
                    count += 1
            return count

        for roles in (self.premium_roles, self.required_roles):
            roles_removed += await remove_invalid_roles(roles)

        if roles_removed != 0:
            await ctx.send(f"Removed {roles_removed} invalid role(s)")
        else:
            await ctx.send("No invalid roles to remove")

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        # Check if the roles of the member have changed
        if before.roles == after.roles:
            return

        if not self.required_roles:
            return

        await remove_roles_if_necessary(after, self.required_roles, self.premium_roles)


async def setup(bot):
    await bot.add_cog(PremiumRoles(bot))
