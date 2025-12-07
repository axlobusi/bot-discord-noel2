import discord
from discord.ext import commands
from discord import app_commands
from cogs.utils import Utils
import asyncio

class Broadcast(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.broadcast_file = "./data/broadcast.json"
        self.broadcast_data = Utils.load_json(self.broadcast_file)

    def save_data(self):
        """Sauvegarde les données de broadcast."""
        Utils.save_json(self.broadcast_file, self.broadcast_data)

    @app_commands.command(name="broadcast", description="🔒 ADMIN : Envoie un message à tous les membres du serveur")
    @app_commands.describe(
        titre="Le titre de l'embed",
        description="La description du message",
        couleur="Couleur de l'embed (red, blue, green, gold, purple)",
        image="URL de l'image à afficher (optionnel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def broadcast(
        self, 
        interaction: discord.Interaction, 
        titre: str, 
        description: str,
        couleur: str = "blue",
        image: str = None
    ):
        """Envoie un embed personnalisé en DM à tous les membres."""

        # Différer la réponse car l'envoi peut prendre du temps
        await interaction.response.defer(ephemeral=True)

        # Définir la couleur
        color_map = {
            "red": discord.Color.red(),
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "gold": discord.Color.gold(),
            "purple": discord.Color.purple(),
            "orange": discord.Color.orange(),
        }
        embed_color = color_map.get(couleur.lower(), discord.Color.blue())

        # Créer l'embed
        embed = discord.Embed(
            title=titre,
            description=description,
            color=embed_color
        )

        # Ajouter l'image si fournie
        if image:
            if image.startswith("http://") or image.startswith("https://"):
                embed.set_image(url=image)
            else:
                await interaction.followup.send(
                    "⚠️ L'URL de l'image doit commencer par http:// ou https://",
                    ephemeral=True
                )
                return

        # Ajouter un footer avec le nom du serveur
        embed.set_footer(
            text=f"Message de {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        # Récupérer tous les membres du serveur (hors bots)
        members = [member for member in interaction.guild.members if not member.bot]

        # Compteurs
        success = 0
        failed = 0

        # Message de progression
        progress_msg = await interaction.followup.send(
            f"📤 Envoi en cours... 0/{len(members)}",
            ephemeral=True
        )

        # Envoyer à chaque membre
        for i, member in enumerate(members, start=1):
            try:
                await member.send(embed=embed)
                success += 1

                # Mettre à jour le message de progression tous les 10 messages
                if i % 10 == 0 or i == len(members):
                    await progress_msg.edit(
                        content=f"📤 Envoi en cours... {i}/{len(members)}\n✅ Réussis: {success} | ❌ Échecs: {failed}"
                    )

                # Petit délai pour éviter le rate limit
                await asyncio.sleep(0.5)

            except discord.Forbidden:
                # L'utilisateur a bloqué les DMs
                failed += 1
            except Exception as e:
                print(f"❌ Erreur pour {member.name}: {e}")
                failed += 1

        # Message final
        final_embed = discord.Embed(
            title="✅ Broadcast terminé !",
            color=discord.Color.green()
        )
        final_embed.add_field(name="✅ Envoyés", value=str(success), inline=True)
        final_embed.add_field(name="❌ Échecs", value=str(failed), inline=True)
        final_embed.add_field(name="📊 Total", value=str(len(members)), inline=True)

        await progress_msg.edit(content=None, embed=final_embed)

        # Sauvegarder l'historique
        guild_id = str(interaction.guild.id)
        if guild_id not in self.broadcast_data:
            self.broadcast_data[guild_id] = []

        self.broadcast_data[guild_id].append({
            "author": str(interaction.user.id),
            "titre": titre,
            "description": description,
            "success": success,
            "failed": failed,
            "timestamp": discord.utils.utcnow().isoformat()
        })

        self.save_data()

    @app_commands.command(name="broadcast_preview", description="🔒 ADMIN : Prévisualise un broadcast sans l'envoyer")
    @app_commands.describe(
        titre="Le titre de l'embed",
        description="La description du message",
        couleur="Couleur de l'embed (red, blue, green, gold, purple)",
        image="URL de l'image à afficher (optionnel)"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def broadcast_preview(
        self, 
        interaction: discord.Interaction, 
        titre: str, 
        description: str,
        couleur: str = "blue",
        image: str = None
    ):
        """Prévisualise un broadcast avant de l'envoyer."""

        # Définir la couleur
        color_map = {
            "red": discord.Color.red(),
            "blue": discord.Color.blue(),
            "green": discord.Color.green(),
            "gold": discord.Color.gold(),
            "purple": discord.Color.purple(),
            "orange": discord.Color.orange(),
        }
        embed_color = color_map.get(couleur.lower(), discord.Color.blue())

        # Créer l'embed
        embed = discord.Embed(
            title=titre,
            description=description,
            color=embed_color
        )

        # Ajouter l'image si fournie
        if image:
            if image.startswith("http://") or image.startswith("https://"):
                embed.set_image(url=image)
            else:
                await interaction.response.send_message(
                    "⚠️ L'URL de l'image doit commencer par http:// ou https://",
                    ephemeral=True
                )
                return

        # Ajouter un footer
        embed.set_footer(
            text=f"Message de {interaction.guild.name}",
            icon_url=interaction.guild.icon.url if interaction.guild.icon else None
        )

        # Envoyer la prévisualisation
        members_count = len([m for m in interaction.guild.members if not m.bot])

        await interaction.response.send_message(
            f"👀 **Prévisualisation du broadcast**\nCe message sera envoyé à **{members_count} membre(s)**",
            embed=embed,
            ephemeral=True
        )

    @app_commands.command(name="broadcast_history", description="🔒 ADMIN : Affiche l'historique des broadcasts")
    @app_commands.checks.has_permissions(administrator=True)
    async def broadcast_history(self, interaction: discord.Interaction):
        """Affiche l'historique des broadcasts du serveur."""
        guild_id = str(interaction.guild.id)

        if guild_id not in self.broadcast_data or not self.broadcast_data[guild_id]:
            await interaction.response.send_message(
                "❌ Aucun broadcast n'a été envoyé sur ce serveur.",
                ephemeral=True
            )
            return

        history = self.broadcast_data[guild_id]

        embed = discord.Embed(
            title="📜 Historique des Broadcasts",
            description=f"{len(history)} broadcast(s) envoyé(s)",
            color=discord.Color.blue()
        )

        # Afficher les 5 derniers
        for i, broadcast in enumerate(reversed(history[-5:]), start=1):
            author = interaction.guild.get_member(int(broadcast["author"]))
            author_name = author.display_name if author else "Utilisateur inconnu"

            embed.add_field(
                name=f"📨 {broadcast['titre']}",
                value=(
                    f"**Par:** {author_name}\n"
                    f"**Envoyés:** {broadcast['success']} ✅ | {broadcast['failed']} ❌\n"
                    f"**Date:** <t:{int(discord.utils.parse_time(broadcast['timestamp']).timestamp())}:R>"
                ),
                inline=False
            )

        if len(history) > 5:
            embed.set_footer(text=f"+ {len(history) - 5} autre(s) broadcast(s)")

        await interaction.response.send_message(embed=embed, ephemeral=True)

async def setup(bot):
    await bot.add_cog(Broadcast(bot))