import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import os

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

@bot.tree.command(name="create_event", description="Create a new event (interactive setup)")
async def create_event(interaction: discord.Interaction, event_name: str):
    """
    Start creating a new event with interactive setup
    """
    modal = EventSetupModal(event_name)
    await interaction.response.send_modal(modal)

class EventSetupModal(discord.ui.Modal, title='Event Setup'):
    def __init__(self, event_name: str):
        super().__init__()
        self.event_name_input.default = event_name
    
    event_name_input = discord.ui.TextInput(
        label='Event Name',
        placeholder='Enter event name...',
        max_length=100
    )
    
    description = discord.ui.TextInput(
        label='Description',
        placeholder='Enter event description...',
        style=discord.TextStyle.paragraph,
        max_length=500
    )
    
    event_time = discord.ui.TextInput(
        label='Event Time',
        placeholder='YYYY-MM-DD HH:MM (like 2024-12-25 20:00)',
        max_length=16
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            # Parse the time to validate it
            event_datetime = datetime.strptime(self.event_time.value, "%Y-%m-%d %H:%M")
            
            # Create temporary event data
            temp_event = {
                'name': self.event_name_input.value,
                'description': self.description.value,
                'datetime': event_datetime,
                'type': None,  # Will be set in next step
                'core_role_limits': {},
                'special_role_limits': {},
                'participants': {},
                'channel_id': interaction.channel.id,
                'reminded_1h': False,
                'reminded_30m': False
            }
            
            # Show event type selection
            view = EventTypeSelectionView(temp_event)
            embed = discord.Embed(
                title="🎮 Step 2: Select Event Type",
                description=f"**Event:** {temp_event['name']}\n**Description:** {temp_event['description']}\n**Time:** {event_datetime.strftime('%Y-%m-%d %H:%M')}",
                color=0x0099ff
            )
            await interaction.response.send_message(embed=embed, view=view, ephemeral=True)
            
        except ValueError:
            await interaction.response.send_message("❌ Invalid time format! Use: YYYY-MM-DD HH:MM (like 2024-12-25 20:00)", ephemeral=True)

class EventTypeSelectionView(discord.ui.View):
    def __init__(self, temp_event):
        super().__init__(timeout=300)
        self.temp_event = temp_event
    
    @discord.ui.select(
        placeholder="Choose event type...",
        options=[
            discord.SelectOption(label="Fractals", emoji="🔺"),
            discord.SelectOption(label="Raid", emoji="⚔️"),
            discord.SelectOption(label="WvW", emoji="🏰"),
            discord.SelectOption(label="Meta", emoji="🌟"),
            discord.SelectOption(label="Guild Missions", emoji="🏛️"),
            discord.SelectOption(label="PvP", emoji="⚡"),
            discord.SelectOption(label="Chill Sessions", emoji="😎"),
        ]
    )
    async def select_event_type(self, interaction: discord.Interaction, select: discord.ui.Select):
        self.temp_event['type'] = select.values[0]
        
        # Move to role selection
        view = RoleSetupView(self.temp_event)
        embed = discord.Embed(
            title="🎯 Step 3: Add Roles",
            description=f"**Event:** {self.temp_event['name']}\n**Type:** {self.temp_event['type']}\n**Time:** {self.temp_event['datetime'].strftime('%Y-%m-%d %H:%M')}\n\n**Current Roles:** None yet",
            color=0x00ff00
        )
        await interaction.response.edit_message(embed=embed, view=view)

class RoleSetupView(discord.ui.View):
    def __init__(self, temp_event):
        super().__init__(timeout=600)
        self.temp_event = temp_event
        self.update_embed_content()
    
    def update_embed_content(self):
        # Create embed content showing current roles
        core_roles_text = []
        special_roles_text = []
        
        for role, count in self.temp_event['core_role_limits'].items():
            if count > 0:
                core_roles_text.append(f"• {role}: {count}")
        
        for role, count in self.temp_event['special_role_limits'].items():
            if count > 0:
                special_roles_text.append(f"• {role}: {count}")
        
        core_text = "\n".join(core_roles_text) if core_roles_text else "None"
        special_text = "\n".join(special_roles_text) if special_roles_text else "None"
        
        return f"**Event:** {self.temp_event['name']}\n**Type:** {self.temp_event['type']}\n**Time:** {self.temp_event['datetime'].strftime('%Y-%m-%d %H:%M')}\n\n**Core Roles:**\n{core_text}\n\n**Special Roles:**\n{special_text}"
    
    @discord.ui.select(
        placeholder="Select a role to add...",
        options=[
            # Core roles
            discord.SelectOption(label="Fill", emoji="👥", description="Core role"),
            discord.SelectOption(label="Heal", emoji="❤️", description="Core role"),
            discord.SelectOption(label="Qheal", emoji="💚", description="Core role"),
            discord.SelectOption(label="Aheal", emoji="💙", description="Core role"),
            discord.SelectOption(label="PowerDPS", emoji="⚔️", description="Core role"),
            discord.SelectOption(label="CondiDPS", emoji="🗡️", description="Core role"),
            discord.SelectOption(label="QDPS", emoji="🏹", description="Core role"),
            discord.SelectOption(label="ADPS", emoji="🔥", description="Core role"),
            discord.SelectOption(label="Tank", emoji="🛡️", description="Core role"),
            # Special roles (most common ones)
            discord.SelectOption(label="Kite", emoji="🏃", description="Special role"),
            discord.SelectOption(label="Cannons", emoji="💣", description="Special role"),
            discord.SelectOption(label="Reflect", emoji="🔄", description="Special role"),
            discord.SelectOption(label="Tower", emoji="🗼", description="Special role"),
            discord.SelectOption(label="Back Warg", emoji="🐺", description="Special role"),
            discord.SelectOption(label="Hand Kite", emoji="✋", description="Special role"),
            discord.SelectOption(label="Super Speed", emoji="⚡", description="Special role"),
            discord.SelectOption(label="Throw", emoji="🎯", description="Special role"),
            discord.SelectOption(label="G1", emoji="1️⃣", description="Special role"),
            discord.SelectOption(label="G2 Backups", emoji="2️⃣", description="Special role"),
            discord.SelectOption(label="G3", emoji="3️⃣", description="Special role"),
            discord.SelectOption(label="Lamps", emoji="💡", description="Special role"),
        ]
    )
    async def select_role(self, interaction: discord.Interaction, select: discord.ui.Select):
        selected_role = select.values[0]
        modal = RoleQuantityModal(selected_role, self.temp_event, self)
        await interaction.response.send_modal(modal)
    
    @discord.ui.button(label="Finish Event Creation", style=discord.ButtonStyle.green, emoji="✅")
    async def finish_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Check if at least one core role is added
        total_core_slots = sum(self.temp_event['core_role_limits'].values())
        if total_core_slots == 0:
            await interaction.response.send_message("❌ You need at least 1 core role slot!", ephemeral=True)
            return
        
        try:
            ensure_events_dict()
            
            # Create the final event
            event_id = len(events) + 1
            events[event_id] = self.temp_event.copy()
            
            # Initialize all role limits with defaults
            all_core_roles = ['Fill', 'Heal', 'Qheal', 'Aheal', 'PowerDPS', 'CondiDPS', 'QDPS', 'ADPS', 'Tank']
            all_special_roles = ['Kite', 'Cannons', 'Reflect', 'Tower', 'Back Warg', 'Hand Kite', 'Super Speed', 
                               'Throw', 'G1', 'G2 Backups', 'G3', 'Lamps', 'Kite/Push', 'Off Tank', 'Portals', 'Pylons']
            
            for role in all_core_roles:
                if role not in events[event_id]['core_role_limits']:
                    events[event_id]['core_role_limits'][role] = 0
            
            for role in all_special_roles:
                if role not in events[event_id]['special_role_limits']:
                    events[event_id]['special_role_limits'][role] = 0
            
            # Create the event embed and post it
            embed = create_event_embed(event_id)
            view = EventView(event_id)
            
            # Post to the original channel (not ephemeral)
            channel = interaction.channel
            message = await channel.send(embed=embed, view=view)
            events[event_id]['message_id'] = message.id
            
            await interaction.response.edit_message(
                content="✅ **Event Created Successfully!**", 
                embed=None, 
                view=None
            )
            
        except Exception as e:
            print(f"Error creating event: {e}")
            await interaction.response.send_message("❌ Error creating event!", ephemeral=True)
    
    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red, emoji="❌")
    async def cancel_event(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Event creation cancelled.", embed=None, view=None)

class RoleQuantityModal(discord.ui.Modal, title='Set Role Quantity'):
    def __init__(self, role_name: str, temp_event: dict, parent_view: RoleSetupView):
        super().__init__()
        self.role_name = role_name
        self.temp_event = temp_event
        self.parent_view = parent_view
        self.quantity.label = f'How many {role_name}?'
    
    quantity = discord.ui.TextInput(
        label='Quantity',
        placeholder='Enter number (e.g., 2)',
        max_length=2
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            qty = int(self.quantity.value)
            if qty < 0:
                await interaction.response.send_message("❌ Quantity must be 0 or positive!", ephemeral=True)
                return
            
            # Determine if it's a core or special role
            core_roles = ['Fill', 'Heal', 'Qheal', 'Aheal', 'PowerDPS', 'CondiDPS', 'QDPS', 'ADPS', 'Tank']
            
            if self.role_name in core_roles:
                self.temp_event['core_role_limits'][self.role_name] = qty
            else:
                self.temp_event['special_role_limits'][self.role_name] = qty
            
            # Update the embed
            embed_content = self.parent_view.update_embed_content()
            embed = discord.Embed(
                title="🎯 Step 3: Add Roles",
                description=embed_content,
                color=0x00ff00
            )
            
            if qty == 0:
                embed.add_field(name="✅ Role Removed", value=f"{self.role_name} removed from event", inline=False)
            else:
                embed.add_field(name="✅ Role Added", value=f"{self.role_name}: {qty} slots", inline=False)
            
            await interaction.response.edit_message(embed=embed, view=self.parent_view)
            
        except ValueError:
            await interaction.response.send_message("❌ Please enter a valid number!", ephemeral=True)

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
    import os
    bot.run(os.getenv('BOT_TOKEN'))
