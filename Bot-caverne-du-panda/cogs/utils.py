import json
import os
from discord.ext import commands

class Utils(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @staticmethod
    def load_json(filepath):
        """Charge un fichier JSON. Retourne un dict vide si le fichier n'existe pas."""
        if not os.path.exists(filepath):
            return {}
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur lors de la lecture de {filepath}: {e}")
            return {}

    @staticmethod
    def save_json(filepath, data):
        """Sauvegarde des données dans un fichier JSON."""
        try:
            # Créer le dossier si nécessaire
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"❌ Erreur lors de l'écriture dans {filepath}: {e}")
            return False

async def setup(bot):
    await bot.add_cog(Utils(bot))