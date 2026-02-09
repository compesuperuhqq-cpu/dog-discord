Voici le bot complet avec le token directement dans le code :

```python
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from typing import Dict, Optional

# Fichier pour stocker les données
DATA_FILE = "dog_data.json"
DOG_ROLE_NAME = "Dog3"  # Nom du rôle requis pour utiliser les commandes

# ⚠️ REMPLACE CE TOKEN PAR LE TIEN ⚠️
DISCORD_TOKEN = "TON_TOKEN_DISCORD_ICI"

class DogBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.members = True
        super().__init__(command_prefix="!", intents=intents)
        
        # Dictionnaire pour stocker les chiens
        self.dog_owners: Dict[int, Dict] = {}
        
        # Charger les données
        self.load_data()

    def load_data(self):
        """Charge les données depuis le fichier JSON"""
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                self.dog_owners = json.load(f)
                # Convertir les clés de string en int
                self.dog_owners = {int(k): v for k, v in self.dog_owners.items()}

    def save_data(self):
        """Sauvegarde les données dans le fichier JSON"""
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump({str(k): v for k, v in self.dog_owners.items()}, f, ensure_ascii=False, indent=2)

    async def setup_hook(self):
        """Setup des commandes slash"""
        await self.tree.sync()
        print(f"✅ Bot connecté en tant que {self.user}")
        
        # Restaurer les nicknames au démarrage
        await self.restore_dog_status()

    async def restore_dog_status(self):
        """Restaurer le statut de chien au démarrage"""
        for guild in self.guilds:
            for dog_id, data in self.dog_owners.items():
                member = guild.get_member(dog_id)
                if member:
                    owner = guild.get_member(data["owner_id"])
                    if owner:
                        await self.apply_dog_nickname(member, owner)
    
    async def apply_dog_nickname(self, member: discord.Member, owner: discord.Member):
        """Applique le nickname de chien"""
        try:
            nickname = f"🐶 chien de {owner.display_name}"
            if len(nickname) > 32:
                nickname = f"🐶 chien de {owner.display_name[:20]}"
            await member.edit(nick=nickname)
        except discord.Forbidden:
            print(f"❌ Permission refusée pour {member.name}")
        except discord.HTTPException as e:
            print(f"❌ Erreur HTTP: {e}")

    async def remove_dog_nickname(self, member: discord.Member):
        """Retire le nickname de chien"""
        try:
            # Récupérer le nom original depuis les données
            if member.id in self.dog_owners:
                original_nick = self.dog_owners[member.id].get("original_nick", "")
                await member.edit(nick=original_nick if original_nick else None)
        except discord.Forbidden:
            print(f"❌ Permission refusée pour {member.name}")
        except discord.HTTPException as e:
            print(f"❌ Erreur HTTP: {e}")

    def has_dog_role(self, member: discord.Member) -> bool:
        """Vérifie si un membre a le rôle Dog3"""
        return any(role.name == DOG_ROLE_NAME for role in member.roles)

    async def on_member_update(self, before: discord.Member, after: discord.Member):
        """Empêche les chiens de changer leur nickname"""
        if after.id in self.dog_owners:
            if before.nick != after.nick:
                owner_id = self.dog_owners[after.id]["owner_id"]
                owner = after.guild.get_member(owner_id)
                if owner:
                    # Re-appliquer le nickname de chien
                    await self.apply_dog_nickname(after, owner)

# Initialisation du bot
bot = DogBot()

# Commande pour ajouter un chien
@bot.tree.command(name="dog-add", description="Transforme un membre en ton chien")
@app_commands.describe(membre="Le membre à transformer en chien")
async def dog_add(interaction: discord.Interaction, membre: discord.Member):
    """Commande pour ajouter un chien"""
    
    # Vérifier les permissions
    if not bot.has_dog_role(interaction.user):
        await interaction.response.send_message(
            f"❌ Tu dois avoir le rôle **{DOG_ROLE_NAME}** pour utiliser cette commande!",
            ephemeral=True
        )
        return
    
    # Vérifier si l'utilisateur essaie de se dog-add lui-même
    if membre.id == interaction.user.id:
        await interaction.response.send_message(
            "❌ Tu ne peux pas te transformer en chien toi-même!",
            ephemeral=True
        )
        return
    
    # Vérifier si le membre est déjà un chien
    if membre.id in bot.dog_owners:
        await interaction.response.send_message(
            f"❌ {membre.mention} est déjà un chien!",
            ephemeral=True
        )
        return
    
    # Vérifier si le membre est administrateur
    if membre.guild_permissions.administrator:
        await interaction.response.send_message(
            "❌ Tu ne peux pas transformer un administrateur en chien!",
            ephemeral=True
        )
        return
    
    # Sauvegarder le nickname original
    original_nick = membre.nick
    
    # Ajouter aux données
    bot.dog_owners[membre.id] = {
        "owner_id": interaction.user.id,
        "original_nick": original_nick,
        "owner_name": interaction.user.name
    }
    
    # Appliquer le nouveau nickname
    await bot.apply_dog_nickname(membre, interaction.user)
    
    # Sauvegarder les données
    bot.save_data()
    
    await interaction.response.send_message(
        f"✅ {membre.mention} est maintenant ton chien! 🐶\n"
        f"Son surnom a été changé en **'chien de {interaction.user.display_name}'**\n"
        f"Seul toi peut le libérer avec `/dog-del @{membre.name}`",
        ephemeral=False
    )

# Commande pour retirer un chien
@bot.tree.command(name="dog-del", description="Libère un de tes chiens")
@app_commands.describe(membre="Le chien à libérer")
async def dog_del(interaction: discord.Interaction, membre: discord.Member):
    """Commande pour retirer le statut de chien"""
    
    # Vérifier si le membre est un chien
    if membre.id not in bot.dog_owners:
        await interaction.response.send_message(
            f"❌ {membre.mention} n'est pas un chien!",
            ephemeral=True
        )
        return
    
    # Vérifier si l'utilisateur est le propriétaire
    dog_data = bot.dog_owners[membre.id]
    if dog_data["owner_id"] != interaction.user.id:
        await interaction.response.send_message(
            f"❌ Tu n'es pas le maître de {membre.mention}!\n"
            f"Seul <@{dog_data['owner_id']}> peut le libérer.",
            ephemeral=True
        )
        return
    
    # Retirer le statut de chien
    await bot.remove_dog_nickname(membre)
    
    # Supprimer des données
    del bot.dog_owners[membre.id]
    bot.save_data()
    
    await interaction.response.send_message(
        f"✅ {membre.mention} a été libéré! 🎉\n"
        f"Il n'est plus ton chien.",
        ephemeral=False
    )

# Commande pour voir tous les chiens
@bot.tree.command(name="dog-list", description="Voir tous les chiens et leurs maîtres")
async def dog_list(interaction: discord.Interaction):
    """Commande pour lister tous les chiens"""
    
    if not bot.dog_owners:
        await interaction.response.send_message(
            "🐕 Il n'y a aucun chien pour le moment!",
            ephemeral=False
        )
        return
    
    embed = discord.Embed(
        title="🐶 Liste des Chiens",
        color=discord.Color.gold(),
        description="Voici tous les chiens et leurs maîtres:"
    )
    
    for dog_id, data in bot.dog_owners.items():
        dog_member = interaction.guild.get_member(dog_id)
        owner_member = interaction.guild.get_member(data["owner_id"])
        
        if dog_member and owner_member:
            embed.add_field(
                name=f"🐕 {dog_member.display_name}",
                value=f"**Maître:** {owner_member.mention}\n"
                      f"**Nom original:** {data.get('original_nick', 'Aucun')}",
                inline=False
            )
    
    await interaction.response.send_message(embed=embed, ephemeral=False)

# Commande pour voir ses chiens
@bot.tree.command(name="dog-my", description="Voir tes chiens")
async def dog_my(interaction: discord.Interaction):
    """Commande pour voir ses propres chiens"""
    
    my_dogs = {}
    for dog_id, data in bot.dog_owners.items():
        if data["owner_id"] == interaction.user.id:
            my_dogs[dog_id] = data
    
    if not my_dogs:
        await interaction.response.send_message(
            "🐕 Tu n'as pas de chien pour le moment!\n"
            "Utilise `/dog-add @membre` pour en ajouter un.",
            ephemeral=True
        )
        return
    
    embed = discord.Embed(
        title=f"🐶 Tes Chiens ({len(my_dogs)})",
        color=discord.Color.blue(),
        description="Voici les membres qui sont tes chiens:"
    )
    
    for dog_id, data in my_dogs.items():
        dog_member = interaction.guild.get_member(dog_id)
        if dog_member:
            embed.add_field(
                name=f"🐕 {dog_member.display_name}",
                value=f"**Nom original:** {data.get('original_nick', 'Aucun')}",
                inline=False
            )
    
    embed.set_footer(text="Utilise /dog-del @membre pour libérer un chien")
    await interaction.response.send_message(embed=embed, ephemeral=True)

# Événement quand le bot est prêt
@bot.event
async def on_ready():
    """Quand le bot est prêt"""
    print(f"🐶 Bot Dog est prêt!")
    print(f"Connecté en tant que: {bot.user}")
    print(f"ID: {bot.user.id}")
    print(f"Servers: {len(bot.guilds)}")
    
    # Vérifier si le rôle Dog3 existe, sinon le créer
    for guild in bot.guilds:
        dog_role = discord.utils.get(guild.roles, name=DOG_ROLE_NAME)
        if not dog_role:
            try:
                dog_role = await guild.create_role(
                    name=DOG_ROLE_NAME,
                    color=discord.Color.gold(),
                    reason="Rôle requis pour utiliser les commandes /dog"
                )
                print(f"✅ Rôle '{DOG_ROLE_NAME}' créé dans {guild.name}")
            except discord.Forbidden:
                print(f"❌ Permission refusée pour créer le rôle dans {guild.name}")

# Événement quand un membre rejoint
@bot.event
async def on_member_join(member: discord.Member):
    """Quand un membre rejoint"""
    # Vérifier si c'est un chien qui rejoint
    if member.id in bot.dog_owners:
        owner_id = bot.dog_owners[member.id]["owner_id"]
        owner = member.guild.get_member(owner_id)
        if owner:
            await bot.apply_dog_nickname(member, owner)

# Gestion des erreurs
@dog_add.error
async def dog_add_error(interaction: discord.Interaction, error):
    """Gestion des erreurs pour dog-add"""
    if isinstance(error, app_commands.errors.MissingPermissions):
        await interaction.response.send_message(
            f"❌ Tu n'as pas la permission d'utiliser cette commande!\n"
            f"Tu dois avoir le rôle **{DOG_ROLE_NAME}**.",
            ephemeral=True
        )
    else:
        await interaction.response.send_message(
            f"❌ Une erreur est survenue: {str(error)}",
            ephemeral=True
        )

# Lancer le bot
print("🐶 Démarrage du Bot Dog...")
print("⚠️ ATTENTION: Assure-toi d'avoir remplacé le token dans le code!")
bot.run(DISCORD_TOKEN)
```

## Comment utiliser le bot :

### 1. Remplace le token
Dans le code, remplace cette ligne :
```python
DISCORD_TOKEN = "TON_TOKEN_DISCORD_ICI"
```

Par ton token réel qui ressemble à ça :
```python
DISCORD_TOKEN = "MTEyMzQ1Njc4OTAxMjM0NTY3OA.GabcdefghijklmnopqrstuvwxyzABCDEF"
```

### 2. Crée un bot Discord
1. Va sur https://discord.com/developers/applications
2. Clique sur "New Application"
3. Donne un nom à ton bot
4. Va dans l'onglet "Bot"
5. Clique sur "Reset Token" puis "Copy"
6. Colle le token dans le code

### 3. Active les intents
Sur le site Discord Developer :
1. Dans l'onglet "Bot"
2. Active ces options :
   - PRESENCE INTENT
   - SERVER MEMBERS INTENT
   - MESSAGE CONTENT INTENT

### 4. Invite le bot sur ton serveur
1. Va dans l'onglet "OAuth2" > "URL Generator"
2. Sélectionne "bot" et "applications.commands"
3. Choisis les permissions :
   - Manage Nicknames
   - Manage Roles
   - Send Messages
   - Embed Links
4. Utilise le lien généré pour inviter le bot

### 5. Lance le bot
```bash
python bot.py
```

Le bot va :
- Se connecter à Discord
- Créer automatiquement le rôle `Dog3`
- Synchroniser les commandes `/dog-add`, `/dog-del`, `/dog-list`, `/dog-my`

### 6. Donne le rôle aux utilisateurs
Donne le rôle `Dog3` aux membres qui peuvent utiliser les commandes.

**⚠️ IMPORTANT :** Ne partage jamais ton token avec personne !
