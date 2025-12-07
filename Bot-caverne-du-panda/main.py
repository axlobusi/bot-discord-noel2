import os
import discord
from discord.ext import commands, tasks

# ---- INTENTS ----
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.invites = True

# ---- BOT ----
bot = commands.Bot(command_prefix="!", intents=intents)

# ---- KEEP AWAKE FUNCTION ----
@tasks.loop(minutes=10)
async def keep_awake():
    """Empêche le bot de s'endormir sur Render."""
    print("🔄 Keep-awake ping - Bot toujours actif !")

# ---- LOAD COGS ----
async def load_cogs():
    print("📦 Chargement des cogs...")
    cogs_loaded = 0
    for filename in os.listdir("./cogs"):
        if filename.endswith(".py") and not filename.startswith("_"):
            try:
                await bot.load_extension(f"cogs.{filename[:-3]}")
                print(f"   ✅ {filename} chargé avec succès")
                cogs_loaded += 1
            except Exception as e:
                print(f"   ❌ Erreur lors du chargement de {filename}: {e}")
    print(f"📊 Total : {cogs_loaded} cog(s) chargé(s)\n")

# ---- ON READY ----
@bot.event
async def on_ready():
    print(f"\n{'='*50}")
    print(f"🔵 Le bot est connecté en tant que {bot.user}")
    print(f"📊 Connecté à {len(bot.guilds)} serveur(s)")
    print(f"{'='*50}\n")

    # Démarrer la boucle keep-awake
    if not keep_awake.is_running():
        keep_awake.start()
        print("✅ Système keep-awake activé (ping toutes les 10 minutes)")

    # Synchroniser les commandes slash
    try:
        synced = await bot.tree.sync()
        print(f"✅ {len(synced)} commande(s) slash synchronisée(s)")
        print(f"\n📋 Liste des commandes disponibles :")
        for cmd in synced:
            print(f"   • /{cmd.name} - {cmd.description}")
        print(f"\n{'='*50}")
    except Exception as e:
        print(f"❌ Erreur lors de la synchronisation : {e}")

    print("✅ Bot opérationnel et protégé contre l'endormissement !\n")

# ---- START BOT ----
async def main():
    await load_cogs()
    token = os.environ.get("Token_bot")
    if not token:
        raise ValueError("❌ Le token n'est pas défini dans les variables d'environnement.")
    await bot.start(token)

# ---- RUN ----
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
