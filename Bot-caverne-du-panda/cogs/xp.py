import discord
from discord.ext import commands
from discord import app_commands
from cogs.utils import Utils
import time
import math
from typing import Literal

class XP(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.xp_file = "./data/xp.json"
        self.xp_data = Utils.load_json(self.xp_file)

    def save_data(self):
        """Sauvegarde les données XP."""
        Utils.save_json(self.xp_file, self.xp_data)

    def get_guild_data(self, guild_id):
        """Récupère ou initialise les données d'un serveur."""
        guild_id = str(guild_id)
        if guild_id not in self.xp_data:
            self.xp_data[guild_id] = {
                "users": {},
                "boosts": {},
                "cooldown": 60
            }
        return self.xp_data[guild_id]

    def get_user_data(self, guild_id, user_id):
        """Récupère ou initialise les données d'un utilisateur."""
        guild_data = self.get_guild_data(guild_id)
        user_id = str(user_id)
        if user_id not in guild_data["users"]:
            guild_data["users"][user_id] = {
                "xp": 0,
                "level": 1,
                "last_message": 0
            }
        return guild_data["users"][user_id]

    def calculate_level(self, xp):
        """Calcule le niveau en fonction de l'XP."""
        return int(math.sqrt(xp / 100)) + 1

    def xp_for_next_level(self, level):
        """Calcule l'XP nécessaire pour atteindre le prochain niveau."""
        return (level ** 2) * 100

    @commands.Cog.listener()
    async def on_message(self, message):
        """Ajoute de l'XP quand un utilisateur envoie un message."""
        if message.author.bot or not message.guild:
            return

        guild_id = message.guild.id
        user_id = message.author.id
        channel_id = str(message.channel.id)

        guild_data = self.get_guild_data(guild_id)
        user_data = self.get_user_data(guild_id, user_id)

        # Vérifier le cooldown
        current_time = time.time()
        cooldown = guild_data.get("cooldown", 60)
        if current_time - user_data["last_message"] < cooldown:
            return

        # Calculer l'XP à ajouter
        base_xp = 5
        multiplier = guild_data["boosts"].get(channel_id, 1.0)
        xp_gained = int(base_xp * multiplier)

        # Ajouter l'XP
        user_data["xp"] += xp_gained
        user_data["last_message"] = current_time

        # Vérifier si l'utilisateur monte de niveau
        old_level = user_data["level"]
        new_level = self.calculate_level(user_data["xp"])

        if new_level > old_level:
            user_data["level"] = new_level
            await message.channel.send(
                f"🎉 **{message.author.mention}** vient de passer au niveau **{new_level}** ! Bravo ! 🎊"
            )

        self.save_data()

    @app_commands.command(name="xp", description="Affiche ton XP et ton niveau")
    async def xp_show(self, interaction: discord.Interaction, membre: discord.Member = None):
        """Affiche l'XP d'un utilisateur."""
        target = membre or interaction.user
        user_data = self.get_user_data(interaction.guild.id, target.id)

        xp = user_data["xp"]
        level = user_data["level"]
        xp_needed = self.xp_for_next_level(level)
        xp_current_level = self.xp_for_next_level(level - 1)
        xp_progress = xp - xp_current_level
        xp_required = xp_needed - xp_current_level

        # Créer un embed propre
        embed = discord.Embed(
            title=f"📊 Statistiques de {target.display_name}",
            color=discord.Color.blue()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="🎮 Niveau", value=f"**{level}**", inline=True)
        embed.add_field(name="⭐ XP Total", value=f"**{xp}**", inline=True)
        embed.add_field(name="📈 Progression", value=f"**{xp_progress}/{xp_required} XP**", inline=False)

        # Barre de progression
        progress_bar_length = 20
        if xp_required > 0:
            filled = int((xp_progress / xp_required) * progress_bar_length)
        else:
            filled = progress_bar_length
        bar = "█" * filled + "░" * (progress_bar_length - filled)
        percentage = int((xp_progress/xp_required)*100) if xp_required > 0 else 100
        embed.add_field(name="Barre de progression", value=f"`{bar}` {percentage}%", inline=False)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="leaderboard", description="Affiche le classement XP du serveur")
    async def leaderboard(self, interaction: discord.Interaction):
        """Affiche le classement des utilisateurs par XP."""
        guild_data = self.get_guild_data(interaction.guild.id)
        users = guild_data["users"]

        # Trier les utilisateurs par XP
        sorted_users = sorted(users.items(), key=lambda x: x[1]["xp"], reverse=True)

        if not sorted_users:
            await interaction.response.send_message("❌ Aucun utilisateur n'a encore d'XP !")
            return

        # Créer l'embed
        embed = discord.Embed(
            title="🏆 Classement XP",
            description="Les membres les plus actifs du serveur",
            color=discord.Color.gold()
        )

        # Afficher le top 10
        for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
            member = interaction.guild.get_member(int(user_id))
            if member:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=f"Niveau {data['level']} • {data['xp']} XP",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="boostxp_add", description="🔒 ADMIN : Ajoute un boost XP sur un salon")
    @app_commands.describe(
        salon="Le salon à booster",
        multiplicateur="Le multiplicateur d'XP (ex: 2 pour x2, 3 pour x3)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def boostxp_add(self, interaction: discord.Interaction, salon: discord.TextChannel, multiplicateur: float):
        """Ajoute un boost XP sur un salon."""
        if multiplicateur <= 0:
            await interaction.response.send_message("❌ Le multiplicateur doit être supérieur à 0 !", ephemeral=True)
            return

        guild_data = self.get_guild_data(interaction.guild.id)
        channel_id = str(salon.id)

        guild_data["boosts"][channel_id] = multiplicateur
        self.save_data()

        await interaction.response.send_message(
            f"✅ Boost XP ajouté : {salon.mention} → **x{multiplicateur}** XP"
        )

    @app_commands.command(name="boostxp_remove", description="🔒 ADMIN : Supprime le boost XP d'un salon")
    @app_commands.describe(salon="Le salon dont on veut supprimer le boost")
    @app_commands.checks.has_permissions(administrator=True)
    async def boostxp_remove(self, interaction: discord.Interaction, salon: discord.TextChannel):
        """Supprime le boost XP d'un salon."""
        guild_data = self.get_guild_data(interaction.guild.id)
        channel_id = str(salon.id)

        if channel_id in guild_data["boosts"]:
            del guild_data["boosts"][channel_id]
            self.save_data()
            await interaction.response.send_message(f"✅ Boost XP supprimé pour {salon.mention}")
        else:
            await interaction.response.send_message(f"❌ Aucun boost XP trouvé pour {salon.mention}", ephemeral=True)

    @app_commands.command(name="boostxp_list", description="🔒 ADMIN : Liste tous les salons boostés")
    @app_commands.checks.has_permissions(administrator=True)
    async def boostxp_list(self, interaction: discord.Interaction):
        """Liste tous les salons avec boost XP."""
        guild_data = self.get_guild_data(interaction.guild.id)
        boosts = guild_data["boosts"]

        if not boosts:
            await interaction.response.send_message("❌ Aucun salon n'a de boost XP pour le moment.")
            return

        embed = discord.Embed(
            title="⚡ Salons avec Boost XP",
            color=discord.Color.green()
        )

        for channel_id, multiplier in boosts.items():
            channel = interaction.guild.get_channel(int(channel_id))
            if channel:
                embed.add_field(
                    name=f"#{channel.name}",
                    value=f"**x{multiplier}** XP",
                    inline=True
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="cooldownxp", description="🔒 ADMIN : Définit le cooldown entre les messages pour gagner de l'XP")
    @app_commands.describe(secondes="Nombre de secondes entre chaque message comptant pour l'XP")
    @app_commands.checks.has_permissions(administrator=True)
    async def cooldownxp(self, interaction: discord.Interaction, secondes: int):
        """Définit le cooldown pour gagner de l'XP."""
        if secondes < 0:
            await interaction.response.send_message("❌ Le cooldown ne peut pas être négatif !", ephemeral=True)
            return

        guild_data = self.get_guild_data(interaction.guild.id)
        guild_data["cooldown"] = secondes
        self.save_data()

        await interaction.response.send_message(f"✅ Cooldown XP défini à **{secondes} secondes**")

async def setup(bot):
    await bot.add_cog(XP(bot))