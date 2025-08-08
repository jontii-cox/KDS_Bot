import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import os
from flask import Flask
from threading import Thread

# Create Flask app for Render health checks
app = Flask('')

@app.route('/')
def home():
    return "KDS Bot is online! 🎮"

@app.route('/health')
def health():
    return {"status": "healthy", "bot": str(bot.user) if bot.is_ready() else "connecting"}

def run_flask():
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

def keep_alive():
    t = Thread(target=run_flask)
    t.daemon = True
    t.start()

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Store events (in a real bot, use a database)
events = {}

# Ensure events is always a dictionary
def ensure_events_dict():
    global events
    if not isinstance(events, dict):
        events = {}

# Define core and special roles
CORE_ROLES = [
    'Fill', 'Heal', 'Qheal', 'Aheal', 'PowerDPS', 'CondiDPS', 'QDPS', 'ADPS',
    'Tank'
]
SPECIAL_ROLES = [
    'Kite', 'Cannons', 'Reflect', 'Tower', 'Back Warg', 'Hand Kite',
    'Super Speed', 'Throw', 'G1', 'G2 Backups', 'G3', 'Lamps', 'Kite/Push',
    'Off Tank', 'Portals', 'Pylons'
]

@bot.event
async def on_ready():
    print(f'{bot.user} is online!')
    
    # Start checking for reminders only if not already running
    if not check_events.is_running():
        check_events.start()
    
    # Sync slash commands after starting tasks
    print("Attempting to sync commands...")
    try:
        synced = await bot.tree.sync()
        print(f"Successfully synced {len(synced)} command(s)")
        for cmd in synced:
            print(f"  - {cmd.name}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")
        import traceback
        traceback.print_exc()

# Simple test command to verify sync is working
@bot.tree.command(name="test", description="Simple test command")
async def test_command(interaction: discord.Interaction):
    await interaction.response.send_message("Bot is working! ✅", ephemeral=True)

@bot.tree.command(name="create_event", description="Create a new event with core roles")
async def create_event(
        interaction: discord.Interaction,
        event_name: str,
        event_type: str,
        description: str,
        event_time: str,
        # Core roles only (9 parameters + 4 basic = 13 total, well under 25)
        fill_slots: int = 0,
        heal_slots: int = 0,
        qheal_slots: int = 0,
        aheal_slots: int = 0,
        powerdps_slots: int = 0,
        condidps_slots: int = 0,
        qdps_slots: int = 0,
        adps_slots: int = 0,
        tank_slots: int = 0):
    """
    Create an event with core roles only (use /add_special_roles after to add special roles)
    event_type: Choose from Fractals, Raid, WvW, Meta, Guild Missions, PvP, Chill Sessions
    event_time format: YYYY-MM-DD HH:MM (like 2024-12-25 20:00)
    """
    try:
        # Ensure events is properly initialized
        ensure_events_dict()
        
        # Validate event type
        valid_event_types = [
            "Fractals", "Raid", "WvW", "Meta", "Guild Missions", "PvP",
            "Chill Sessions"
        ]
        if event_type not in valid_event_types:
            await interaction.response.send_message(
                f"Invalid event type! Choose from: {', '.join(valid_event_types)}",
                ephemeral=True)
            return

        # Parse the time
        event_datetime = datetime.strptime(event_time, "%Y-%m-%d %H:%M")

        # Calculate total core slots
        core_slots = (fill_slots + heal_slots + qheal_slots + aheal_slots +
                      powerdps_slots + condidps_slots + qdps_slots +
                      adps_slots + tank_slots)

        if core_slots == 0:
            await interaction.response.send_message(
                "You need at least 1 core role slot!", ephemeral=True)
            return

        # Create the event
        event_id = len(events) + 1
        events[event_id] = {
            'name': event_name,
            'type': event_type,
            'description': description,
            'datetime': event_datetime,
            'core_role_limits': {
                'Fill': fill_slots,
                'Heal': heal_slots,
                'Qheal': qheal_slots,
                'Aheal': aheal_slots,
                'PowerDPS': powerdps_slots,
                'CondiDPS': condidps_slots,
                'QDPS': qdps_slots,
                'ADPS': adps_slots,
                'Tank': tank_slots
            },
            'special_role_limits': {
                'Kite': 0,
                'Cannons': 0,
                'Reflect': 0,
                'Tower': 0,
                'Back Warg': 0,
                'Hand Kite': 0,
                'Super Speed': 0,
                'Throw': 0,
                'G1': 0,
                'G2 Backups': 0,
                'G3': 0,
                'Lamps': 0,
                'Kite/Push': 0,
                'Off Tank': 0,
                'Portals': 0,
                'Pylons': 0
            },
            'participants': {},  # user_id: {'name': name, 'core_role': role, 'special_role': role or None}
            'channel_id': interaction.channel.id,
            'reminded_1h': False,
            'reminded_30m': False
        }

        # Create embed message
        embed = create_event_embed(event_id)

        # Create view with both dropdowns
        view = EventView(event_id)
        await interaction.response.send_message(embed=embed, view=view)

        # Get the message to store its ID
        message = await interaction.original_response()
        events[event_id]['message_id'] = message.id

    except ValueError:
        await interaction.response.send_message(
            "Wrong time format! Use: YYYY-MM-DD HH:MM (like 2024-12-25 20:00)",
            ephemeral=True)

@bot.tree.command(name="add_special_roles", description="Add special roles to an existing event")
async def add_special_roles(
        interaction: discord.Interaction,
        event_id: int,
        kite_slots: int = 0,
        cannons_slots: int = 0,
        reflect_slots: int = 0,
        tower_slots: int = 0,
        back_warg_slots: int = 0,
        hand_kite_slots: int = 0,
        super_speed_slots: int = 0,
        throw_slots: int = 0,
        g1_slots: int = 0,
        g2_backups_slots: int = 0,
        g3_slots: int = 0,
        lamps_slots: int = 0):
    """
    Add special roles to an existing event (12 most common roles)
    Use /list_events to see event IDs
    """
    try:
        ensure_events_dict()
        
        if event_id not in events:
            await interaction.response.send_message(f"Event ID {event_id} not found! Use /list_events to see available events.", ephemeral=True)
            return
        
        # Update special role limits (only the ones available in command)
        events[event_id]['special_role_limits'].update({
            'Kite': kite_slots,
            'Cannons': cannons_slots,
            'Reflect': reflect_slots,
            'Tower': tower_slots,
            'Back Warg': back_warg_slots,
            'Hand Kite': hand_kite_slots,
            'Super Speed': super_speed_slots,
            'Throw': throw_slots,
            'G1': g1_slots,
            'G2 Backups': g2_backups_slots,
            'G3': g3_slots,
            'Lamps': lamps_slots
        })
        
        # Update the original message if possible
        try:
            channel = bot.get_channel(events[event_id]['channel_id'])
            message = await channel.fetch_message(events[event_id]['message_id'])
            
            embed = create_event_embed(event_id)
            view = EventView(event_id)
            
            await message.edit(embed=embed, view=view)
            await interaction.response.send_message(f"✅ Special roles added to event: {events[event_id]['name']}", ephemeral=True)
            
        except:
            await interaction.response.send_message(f"✅ Special roles added to event: {events[event_id]['name']} (Original message couldn't be updated)", ephemeral=True)
            
    except Exception as e:
        print(f"Error in add_special_roles: {e}")
        await interaction.response.send_message("Error adding special roles!", ephemeral=True)

def create_event_embed(event_id):
    """Create the event embed with current participant info"""
    event = events[event_id]

    # Event type emojis
    type_emojis = {
        'Fractals': '🔺',
        'Raid': '⚔️',
        'WvW': '🏰',
        'Meta': '🌟',
        'Guild Missions': '🏛️',
        'PvP': '⚡',
        'Chill Sessions': '😎'
    }

    embed = discord.Embed(
        title=f"{type_emojis.get(event['type'], '🎮')} {event['name']}",
        description=f"**Type:** {event['type']}\n{event['description']}",
        color=0x00ff00)

    embed.add_field(name="📅 Event Time",
                    value=event['datetime'].strftime("%Y-%m-%d %H:%M"),
                    inline=False)

    # Role emojis
    role_emojis = {
        'Fill': '👥',
        'Heal': '❤️',
        'Qheal': '💚',
        'Aheal': '💙',
        'PowerDPS': '⚔️',
        'CondiDPS': '🗡️',
        'QDPS': '🏹',
        'ADPS': '🔥',
        'Tank': '🛡️',
        'Kite': '🏃',
        'Cannons': '💣',
        'Reflect': '🔄',
        'Tower': '🗼',
        'Back Warg': '🐺',
        'Hand Kite': '✋',
        'Super Speed': '⚡',
        'Throw': '🎯',
        'G1': '1️⃣',
        'G2 Backups': '2️⃣',
        'G3': '3️⃣',
        'Lamps': '💡',
        'Kite/Push': '🔄',
        'Off Tank': '🛡️',
        'Portals': '🌀',
        'Pylons': '⚡'
    }

    # Show core roles
    embed.add_field(name="⭐ **CORE ROLES** ⭐", value="", inline=False)
    for role, limit in event['core_role_limits'].items():
        if limit > 0:
            # Count participants with this core role
            current = sum(1 for p in event['participants'].values()
                          if p['core_role'] == role)

            # Get participant names
            participant_names = [
                p['name'] for p in event['participants'].values()
                if p['core_role'] == role
            ]
            if participant_names:
                names_text = "\n".join(participant_names)
            else:
                names_text = "Empty"

            embed.add_field(
                name=f"{role_emojis[role]} {role} ({current}/{limit})",
                value=names_text,
                inline=True)

    # Show special roles if any exist
    special_roles_exist = any(
        limit > 0 for limit in event['special_role_limits'].values())
    if special_roles_exist:
        embed.add_field(name="🎯 **SPECIAL ROLES** 🎯", value="", inline=False)
        for role, limit in event['special_role_limits'].items():
            if limit > 0:
                # Count participants with this special role
                current = sum(1 for p in event['participants'].values()
                              if p.get('special_role') == role)

                # Get participant names
                participant_names = [
                    p['name'] for p in event['participants'].values()
                    if p.get('special_role') == role
                ]
                if participant_names:
                    names_text = "\n".join(participant_names)
                else:
                    names_text = "Empty"

                embed.add_field(
                    name=f"{role_emojis[role]} {role} ({current}/{limit})",
                    value=names_text,
                    inline=True)

    return embed

class CoreRoleSelect(discord.ui.Select):

    def __init__(self, event_id):
        self.event_id = event_id
        event = events[event_id]

        # Only show core roles that have available slots
        options = []
        role_emojis = {
            'Fill': '👥',
            'Heal': '❤️',
            'Qheal': '💚',
            'Aheal': '💙',
            'PowerDPS': '⚔️',
            'CondiDPS': '🗡️',
            'QDPS': '🏹',
            'ADPS': '🔥',
            'Tank': '🛡️'
        }

        for role, limit in event['core_role_limits'].items():
            if limit > 0:
                current = sum(1 for p in event['participants'].values()
                              if p['core_role'] == role)
                available = limit - current

                label = f"{role} ({current}/{limit})"
                if available == 0:
                    label += " - FULL"

                options.append(
                    discord.SelectOption(
                        label=label,
                        value=role,
                        description=f"{available} slots available",
                        emoji=role_emojis[role]))

        super().__init__(placeholder="⭐ Choose your CORE role (required)...",
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        await self.handle_role_selection(interaction, 'core')

    async def handle_role_selection(self, interaction, role_type):
        event = events.get(self.event_id)
        if not event:
            await interaction.response.send_message("Event not found!",
                                                    ephemeral=True)
            return

        user_id = interaction.user.id
        selected_role = self.values[0]

        if role_type == 'core':
            # Check if core role is full
            current_core = sum(1 for p in event['participants'].values()
                               if p['core_role'] == selected_role)
            if current_core >= event['core_role_limits'][selected_role]:
                await interaction.response.send_message(
                    f"{selected_role} is full!", ephemeral=True)
                return

            # Update or create participant entry
            if user_id not in event['participants']:
                event['participants'][user_id] = {
                    'name': interaction.user.display_name,
                    'core_role': selected_role,
                    'special_role': None
                }
            else:
                event['participants'][user_id]['core_role'] = selected_role

        # Update the embed and view
        embed = create_event_embed(self.event_id)
        new_view = EventView(self.event_id)
        await interaction.response.edit_message(embed=embed, view=new_view)

class SpecialRoleSelect(discord.ui.Select):

    def __init__(self, event_id):
        self.event_id = event_id
        event = events[event_id]

        # Only show special roles that have available slots
        options = [
            discord.SelectOption(label="None (Remove special role)",
                                 value="None",
                                 emoji="❌")
        ]

        role_emojis = {
            'Kite': '🏃',
            'Cannons': '💣',
            'Reflect': '🔄',
            'Tower': '🗼',
            'Back Warg': '🐺',
            'Hand Kite': '✋',
            'Super Speed': '⚡',
            'Throw': '🎯',
            'G1': '1️⃣',
            'G2 Backups': '2️⃣',
            'G3': '3️⃣',
            'Lamps': '💡',
            'Kite/Push': '🔄',
            'Off Tank': '🛡️',
            'Portals': '🌀',
            'Pylons': '⚡'
        }

        for role, limit in event['special_role_limits'].items():
            if limit > 0:
                current = sum(1 for p in event['participants'].values()
                              if p.get('special_role') == role)
                available = limit - current

                label = f"{role} ({current}/{limit})"
                if available == 0:
                    label += " - FULL"

                options.append(
                    discord.SelectOption(
                        label=label,
                        value=role,
                        description=f"{available} slots available",
                        emoji=role_emojis[role]))

        super().__init__(placeholder="🎯 Choose special role (optional)...",
                         options=options)

    async def callback(self, interaction: discord.Interaction):
        event = events.get(self.event_id)
        if not event:
            await interaction.response.send_message("Event not found!",
                                                    ephemeral=True)
            return

        user_id = interaction.user.id

        # Check if user has a core role first
        if user_id not in event['participants']:
            await interaction.response.send_message(
                "You must pick a core role first!", ephemeral=True)
            return

        selected_role = self.values[0]

        if selected_role == "None":
            event['participants'][user_id]['special_role'] = None
        else:
            # Check if special role is full
            current_special = sum(1 for p in event['participants'].values()
                                  if p.get('special_role') == selected_role)
            if current_special >= event['special_role_limits'][selected_role]:
                await interaction.response.send_message(
                    f"{selected_role} is full!", ephemeral=True)
                return

            event['participants'][user_id]['special_role'] = selected_role

        # Update the embed and view
        embed = create_event_embed(self.event_id)
        new_view = EventView(self.event_id)
        await interaction.response.edit_message(embed=embed, view=new_view)

class EventView(discord.ui.View):

    def __init__(self, event_id):
        super().__init__(timeout=None)

        # Add core role selector
        self.add_item(CoreRoleSelect(event_id))

        # Add special role selector if any special roles exist
        event = events[event_id]
        special_roles_exist = any(
            limit > 0 for limit in event['special_role_limits'].values())
        if special_roles_exist:
            self.add_item(SpecialRoleSelect(event_id))

    @discord.ui.button(label="Leave Event",
                       style=discord.ButtonStyle.red,
                       emoji="❌")
    async def leave_event(self, interaction: discord.Interaction,
                          button: discord.ui.Button):
        event_id = self.children[
            0].event_id  # Get event_id from first select menu
        event = events.get(event_id)
        if not event:
            await interaction.response.send_message("Event not found!",
                                                    ephemeral=True)
            return

        user_id = interaction.user.id

        if user_id in event['participants']:
            del event['participants'][user_id]

            # Update the embed
            embed = create_event_embed(event_id)
            new_view = EventView(event_id)
            await interaction.response.edit_message(embed=embed, view=new_view)
        else:
            await interaction.response.send_message(
                "You're not in this event!", ephemeral=True)

@tasks.loop(minutes=1)  # Check every minute
async def check_events():
    """Check if any events need reminders"""
    try:
        # Ensure events is properly initialized
        ensure_events_dict()
        
        # Make sure events is a dictionary
        if not isinstance(events, dict) or not events:
            return
            
        now = datetime.now()
        
        # Create a copy of events.items() to avoid modification during iteration
        events_copy = dict(events)
        
        for event_id, event in events_copy.items():
            if not isinstance(event, dict):
                continue
                
            event_time = event.get('datetime')
            if not event_time:
                continue
            
            # 1 hour reminder
            if not event.get('reminded_1h', False) and now >= event_time - timedelta(hours=1):
                await send_reminder(event, "1 hour")
                events[event_id]['reminded_1h'] = True
            
            # 30 minute reminder
            if not event.get('reminded_30m', False) and now >= event_time - timedelta(minutes=30):
                await send_reminder(event, "30 minutes")
                events[event_id]['reminded_30m'] = True
                
    except Exception as e:
        print(f"Error in check_events: {e}")
        # Reset events to empty dict if corrupted
        if not isinstance(events, dict):
            globals()['events'] = {}

async def send_reminder(event, time_left):
    """Send reminder to all participants"""
    channel = bot.get_channel(event['channel_id'])
    if not channel:
        return

    if not event['participants']:
        return

    # Create mention string for all participants
    mentions = [f"<@{user_id}>" for user_id in event['participants'].keys()]
    mention_text = " ".join(mentions)

    embed = discord.Embed(title=f"⏰ Event Reminder: {event['name']}",
                          description=f"Your event starts in {time_left}!",
                          color=0xff9900)

    await channel.send(f"{mention_text}", embed=embed)

# Command to list all events
@bot.tree.command(name="list_events", description="Show all upcoming events")
async def list_events(interaction: discord.Interaction):
    try:
        # Ensure events is properly initialized
        ensure_events_dict()
        
        if not events or len(events) == 0:
            await interaction.response.send_message("No events created yet!", ephemeral=True)
            return
        
        embed = discord.Embed(title="📅 Upcoming Events", color=0x0099ff)
        
        for event_id, event in events.items():
            if not isinstance(event, dict):
                continue
                
            total_participants = len(event.get('participants', {}))
            total_core_slots = sum(event.get('core_role_limits', {}).values())
            
            embed.add_field(
                name=f"{event.get('name', 'Unknown Event')} (ID: {event_id})",
                value=f"**Type:** {event.get('type', 'Unknown')}\n**Time:** {event.get('datetime', 'Unknown').strftime('%Y-%m-%d %H:%M') if event.get('datetime') else 'Unknown'}\n**Participants:** {total_participants}/{total_core_slots}",
                inline=False
            )
        
        await interaction.response.send_message(embed=embed)
    except Exception as e:
        print(f"Error in list_events: {e}")
        await interaction.response.send_message("Error retrieving events!", ephemeral=True)

# Run the bot
if __name__ == "__main__":
    keep_alive()  # Start Flask server
    import time
    time.sleep(2)  # Give Flask time to start
    bot.run(os.getenv('BOT_TOKEN'))
