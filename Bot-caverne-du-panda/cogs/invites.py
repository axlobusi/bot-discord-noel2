import discord
from discord.ext import commands
from discord import app_commands
from cogs.utils import Utils

class Invites(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.invites_file = "./data/invites.json"
        self.invites_data = Utils.load_json(self.invites_file)
        self.invite_cache = {}  # Cache des invitations par serveur

    def save_data(self):
        """Sauvegarde les données d'invitations."""
        Utils.save_json(self.invites_file, self.invites_data)

    def get_guild_data(self, guild_id):
        """Récupère ou initialise les données d'un serveur."""
        guild_id = str(guild_id)
        if guild_id not in self.invites_data:
            self.invites_data[guild_id] = {
                "users": {},
                "settings": {
                    "xp_per_invite": 50,
                    "roles": {}
                }
            }
        return self.invites_data[guild_id]

    def get_user_data(self, guild_id, user_id):
        """Récupère ou initialise les données d'un utilisateur."""
        guild_data = self.get_guild_data(guild_id)
        user_id = str(user_id)
        if user_id not in guild_data["users"]:
            guild_data["users"][user_id] = {
                "invites": 0,
                "left": 0
            }
        return guild_data["users"][user_id]

    @commands.Cog.listener()
    async def on_ready(self):
        """Cache toutes les invitations au démarrage du bot."""
        print("📨 Chargement du cache des invitations...")
        for guild in self.bot.guilds:
            try:
                invites = await guild.invites()
                # Créer un dictionnaire avec code -> uses pour comparaison facile
                self.invite_cache[guild.id] = {invite.code: invite.uses for invite in invites}
                print(f"   ✅ Cache créé pour {guild.name} ({len(invites)} invitations)")
            except Exception as e:
                print(f"   ❌ Erreur pour {guild.name}: {e}")

    @commands.Cog.listener()
    async def on_invite_create(self, invite):
        """Met à jour le cache quand une invitation est créée."""
        try:
            invites = await invite.guild.invites()
            self.invite_cache[invite.guild.id] = {inv.code: inv.uses for inv in invites}
            print(f"📨 Nouvelle invitation créée dans {invite.guild.name}")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du cache : {e}")

    @commands.Cog.listener()
    async def on_invite_delete(self, invite):
        """Met à jour le cache quand une invitation est supprimée."""
        try:
            invites = await invite.guild.invites()
            self.invite_cache[invite.guild.id] = {inv.code: inv.uses for inv in invites}
            print(f"📨 Invitation supprimée dans {invite.guild.name}")
        except Exception as e:
            print(f"❌ Erreur lors de la mise à jour du cache : {e}")

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Détecte qui a invité le membre et donne l'XP."""
        guild = member.guild

        print(f"\n👤 {member.name} a rejoint {guild.name}")

        try:
            # Récupérer les invitations actuelles
            invites_after = await guild.invites()
            invites_before_dict = self.invite_cache.get(guild.id, {})

            print(f"🔍 Cache avant : {invites_before_dict}")

            # Trouver quelle invitation a été utilisée
            inviter_user = None
            used_invite = None

            for invite in invites_after:
                before_uses = invites_before_dict.get(invite.code, 0)
                after_uses = invite.uses

                print(f"🔍 Invite {invite.code}: {before_uses} -> {after_uses}")

                if after_uses > before_uses:
                    inviter_user = invite.inviter
                    used_invite = invite
                    print(f"✅ Inviteur trouvé : {inviter_user.name} (code: {invite.code})")
                    break

            # Mettre à jour le cache IMMÉDIATEMENT
            self.invite_cache[guild.id] = {inv.code: inv.uses for inv in invites_after}
            print(f"🔄 Cache mis à jour")

            if not inviter_user or inviter_user.bot:
                print("❌ Aucun inviteur trouvé ou inviteur est un bot")
                return

            # Récupérer le Member (pas User) depuis le serveur
            inviter = guild.get_member(inviter_user.id)
            if not inviter:
                print(f"❌ Impossible de trouver {inviter_user.name} comme membre du serveur")
                return

            print(f"✅ Inviteur (Member) : {inviter.name}")

            # Mettre à jour les statistiques de l'inviteur
            guild_data = self.get_guild_data(guild.id)
            user_data = self.get_user_data(guild.id, inviter.id)
            user_data["invites"] += 1
            self.save_data()

            print(f"📊 {inviter.name} a maintenant {user_data['invites']} invitations")

            # Donner de l'XP à l'inviteur
            xp_per_invite = guild_data["settings"]["xp_per_invite"]

            # Charger le cog XP pour ajouter l'XP
            xp_cog = self.bot.get_cog("XP")
            if xp_cog:
                xp_user_data = xp_cog.get_user_data(guild.id, inviter.id)
                old_xp = xp_user_data["xp"]
                xp_user_data["xp"] += xp_per_invite
                xp_cog.save_data()
                print(f"✅ {xp_per_invite} XP ajoutés à {inviter.name} ({old_xp} -> {xp_user_data['xp']})")

            # Vérifier les rôles automatiques
            roles_settings = guild_data["settings"]["roles"]
            total_invites = user_data["invites"]

            print(f"\n🔍 === VÉRIFICATION DES RÔLES AUTOMATIQUES ===")
            print(f"🔍 {inviter.name} a {total_invites} invitations")
            print(f"🔍 Rôles configurés : {roles_settings}")

            for role_id, required_invites in roles_settings.items():
                print(f"\n🔍 Test : Rôle ID {role_id} nécessite {required_invites} invites")
                print(f"🔍 Condition : {total_invites} >= {required_invites} ? {total_invites >= required_invites}")

                if total_invites >= required_invites:
                    role = guild.get_role(int(role_id))

                    if not role:
                        print(f"❌ Rôle {role_id} introuvable sur le serveur")
                        continue

                    print(f"✅ Rôle trouvé : {role.name}")
                    print(f"🔍 Rôles actuels de {inviter.name} : {[r.name for r in inviter.roles]}")
                    print(f"🔍 {inviter.name} a déjà ce rôle ? {role in inviter.roles}")

                    if role not in inviter.roles:
                        try:
                            # Vérifier la hiérarchie
                            bot_top_role = guild.me.top_role
                            print(f"🔍 Position du bot : {bot_top_role.name} ({bot_top_role.position})")
                            print(f"🔍 Position du rôle à donner : {role.name} ({role.position})")

                            if bot_top_role.position <= role.position:
                                print(f"❌ Le bot ne peut pas donner le rôle {role.name} (hiérarchie insuffisante)")
                                try:
                                    await inviter.send(
                                        f"⚠️ Tu devrais avoir le rôle **{role.name}** mais le bot n'a pas les permissions nécessaires. Contacte un administrateur !"
                                    )
                                except:
                                    pass
                                continue

                            await inviter.add_roles(role)
                            print(f"✅✅✅ Rôle {role.name} DONNÉ à {inviter.name} !")

                            # Notifier l'inviteur
                            try:
                                await inviter.send(
                                    f"🎉 Félicitations ! Tu as atteint **{total_invites} invitations** et tu as reçu le rôle **{role.name}** sur **{guild.name}** !"
                                )
                                print(f"✅ DM de félicitations envoyé")
                            except:
                                print(f"❌ Impossible d'envoyer un DM à {inviter.name}")
                        except discord.Forbidden:
                            print(f"❌ Pas la permission de donner le rôle {role.name}")
                        except Exception as e:
                            print(f"❌ Erreur lors de l'ajout du rôle : {e}")
                            import traceback
                            traceback.print_exc()
                    else:
                        print(f"ℹ️ {inviter.name} a déjà le rôle {role.name}")

            print(f"=== FIN VÉRIFICATION RÔLES ===\n")

            # Message de bienvenue avec mention de l'inviteur
            try:
                channel = guild.system_channel or guild.text_channels[0]
                await channel.send(
                    f"👋 Bienvenue {member.mention} ! Invité par {inviter.mention} (+{xp_per_invite} XP) 🎉"
                )
                print(f"✅ Message de bienvenue envoyé dans {channel.name}")
            except Exception as e:
                print(f"❌ Erreur lors de l'envoi du message de bienvenue : {e}")

        except Exception as e:
            print(f"❌ ERREUR GLOBALE dans on_member_join : {e}")
            import traceback
            traceback.print_exc()

    @app_commands.command(name="invites", description="Affiche tes invitations ou celles de quelqu'un")
    @app_commands.describe(membre="Le membre dont tu veux voir les invitations (optionnel)")
    async def invites_show(self, interaction: discord.Interaction, membre: discord.Member = None):
        """Affiche les invitations d'un utilisateur."""
        target = membre or interaction.user
        user_data = self.get_user_data(interaction.guild.id, target.id)

        invites = user_data["invites"]
        left = user_data.get("left", 0)
        real_invites = invites - left

        embed = discord.Embed(
            title=f"📨 Invitations de {target.display_name}",
            color=discord.Color.purple()
        )
        embed.set_thumbnail(url=target.display_avatar.url)
        embed.add_field(name="✅ Total d'invitations", value=f"**{invites}**", inline=True)
        embed.add_field(name="❌ Membres partis", value=f"**{left}**", inline=True)
        embed.add_field(name="🎯 Invitations réelles", value=f"**{real_invites}**", inline=True)

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invites_top", description="Affiche le classement des meilleurs inviteurs")
    async def invites_leaderboard(self, interaction: discord.Interaction):
        """Affiche le classement des invitations."""
        guild_data = self.get_guild_data(interaction.guild.id)
        users = guild_data["users"]

        sorted_users = sorted(users.items(), key=lambda x: x[1]["invites"], reverse=True)

        if not sorted_users:
            await interaction.response.send_message("❌ Aucune invitation enregistrée pour le moment !")
            return

        embed = discord.Embed(
            title="🏆 Top Inviteurs",
            description="Les membres qui ont invité le plus de personnes",
            color=discord.Color.gold()
        )

        for i, (user_id, data) in enumerate(sorted_users[:10], start=1):
            member = interaction.guild.get_member(int(user_id))
            if member:
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"**{i}.**"
                invites = data["invites"]
                left = data.get("left", 0)
                real = invites - left
                embed.add_field(
                    name=f"{medal} {member.display_name}",
                    value=f"{invites} invitations ({real} réelles)",
                    inline=False
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invitexp", description="🔒 ADMIN : Définit l'XP gagné par invitation")
    @app_commands.describe(xp="Nombre d'XP à donner par invitation")
    @app_commands.checks.has_permissions(administrator=True)
    async def invite_xp(self, interaction: discord.Interaction, xp: int):
        """Définit l'XP par invitation."""
        if xp < 0:
            await interaction.response.send_message("❌ L'XP ne peut pas être négatif !", ephemeral=True)
            return

        guild_data = self.get_guild_data(interaction.guild.id)
        guild_data["settings"]["xp_per_invite"] = xp
        self.save_data()

        await interaction.response.send_message(f"✅ XP par invitation défini à **{xp} XP**")

    @app_commands.command(name="inviterole_add", description="🔒 ADMIN : Définit un rôle automatique après X invitations")
    @app_commands.describe(
        role="Le rôle à donner automatiquement",
        invitations="Nombre d'invitations requises pour obtenir ce rôle"
    )
    @app_commands.checks.has_permissions(administrator=True)
    async def invite_role_add(self, interaction: discord.Interaction, role: discord.Role, invitations: int):
        """Ajoute un rôle automatique après X invitations."""
        if invitations <= 0:
            await interaction.response.send_message("❌ Le nombre d'invitations doit être supérieur à 0 !", ephemeral=True)
            return

        guild_data = self.get_guild_data(interaction.guild.id)
        role_id = str(role.id)

        guild_data["settings"]["roles"][role_id] = invitations
        self.save_data()

        await interaction.response.send_message(
            f"✅ Rôle automatique ajouté : {role.mention} après **{invitations} invitations**"
        )

    @app_commands.command(name="inviterole_remove", description="🔒 ADMIN : Supprime un rôle automatique")
    @app_commands.describe(role="Le rôle à supprimer des récompenses automatiques")
    @app_commands.checks.has_permissions(administrator=True)
    async def invite_role_remove(self, interaction: discord.Interaction, role: discord.Role):
        """Supprime un rôle automatique."""
        guild_data = self.get_guild_data(interaction.guild.id)
        role_id = str(role.id)

        if role_id in guild_data["settings"]["roles"]:
            del guild_data["settings"]["roles"][role_id]
            self.save_data()
            await interaction.response.send_message(f"✅ Rôle automatique supprimé : {role.mention}")
        else:
            await interaction.response.send_message(f"❌ Ce rôle n'est pas configuré comme récompense automatique", ephemeral=True)

    @app_commands.command(name="inviterole_list", description="🔒 ADMIN : Liste tous les rôles automatiques configurés")
    @app_commands.checks.has_permissions(administrator=True)
    async def invite_role_list(self, interaction: discord.Interaction):
        """Liste tous les rôles automatiques."""
        guild_data = self.get_guild_data(interaction.guild.id)
        roles = guild_data["settings"]["roles"]

        if not roles:
            await interaction.response.send_message("❌ Aucun rôle automatique configuré pour le moment.")
            return

        embed = discord.Embed(
            title="🎁 Rôles Automatiques",
            description="Rôles donnés automatiquement selon le nombre d'invitations",
            color=discord.Color.blue()
        )

        sorted_roles = sorted(roles.items(), key=lambda x: x[1])

        for role_id, required_invites in sorted_roles:
            role = interaction.guild.get_role(int(role_id))
            if role:
                embed.add_field(
                    name=f"{role.name}",
                    value=f"**{required_invites} invitations** requises",
                    inline=True
                )

        await interaction.response.send_message(embed=embed)

    @app_commands.command(name="invites_reset", description="🔒 ADMIN : Reset les invitations d'un membre")
    @app_commands.describe(membre="Le membre dont tu veux reset les invitations")
    @app_commands.checks.has_permissions(administrator=True)
    async def invites_reset(self, interaction: discord.Interaction, membre: discord.Member):
        """Reset les invitations d'un membre."""
        guild_data = self.get_guild_data(interaction.guild.id)
        user_id = str(membre.id)

        if user_id in guild_data["users"]:
            guild_data["users"][user_id] = {"invites": 0, "left": 0}
            self.save_data()
            await interaction.response.send_message(f"✅ Invitations de {membre.mention} remises à zéro")
        else:
            await interaction.response.send_message(f"❌ {membre.mention} n'a aucune invitation enregistrée", ephemeral=True)

async def setup(bot):
    await bot.add_cog(Invites(bot))    