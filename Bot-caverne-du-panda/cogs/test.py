from discord.ext import commands

class Test(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="test")
    async def test(self, ctx):
        """Commande simple pour vérifier que le bot fonctionne."""
        await ctx.send("✅ Le bot est opérationnel !")

async def setup(bot):
    await bot.add_cog(Test(bot))