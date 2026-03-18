import discord
from discord.ext import commands, tasks
from datetime import datetime, timedelta
import asyncio
import os
import json
import random
from threading import Thread
import socket

# ---------------------------------------------------------------------------
# HTTP keepalive server for Railway
# ---------------------------------------------------------------------------

def run_server():
    import http.server
    import socketserver

    class Handler(http.server.SimpleHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(b'KDS Bot is running!')
        def log_message(self, format, *args):
            pass  # suppress noisy HTTP logs

    port = int(os.environ.get('PORT', 8080))
    with socketserver.TCPServer(("", port), Handler) as httpd:
        print(f"HTTP server running on port {port}")
        httpd.serve_forever()

def start_server():
    server_thread = Thread(target=run_server, daemon=True)
    server_thread.start()

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DATA_FILE = '/data/kds_bot_data.json'  # Railway volume mount path

# Tickets awarded per event type on attendance confirmation
POINT_VALUES = {
    'raid': 20,
    'normal': 10,
}

BOSS_TEMPLATES = {
    # Wing 1 - Spirit Vale
    "W1 - Vale Guardian":       {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2, "Condi": 2}, "special": {"G1": 1, "G2 Backups": 1, "G3": 1}},
    "W1 - Gorseval":            {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W1 - Sabetha":             {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Cannons": 2, "Kite/Push": 1}},
    # Wing 2 - Salvation Pass
    "W2 - Slothasor":           {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W2 - Bandit Trio":         {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W2 - Matthias":            {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Back Warg": 1, "Reflect": 1}},
    # Wing 3 - Stronghold of the Faithful
    "W3 - Escort":              {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Super Speed": 1}},
    "W3 - Keep Construct":      {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Tower": 2}},
    "W3 - Xera":                {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    # Wing 4 - Bastion of the Penitent
    "W4 - Cairn":               {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W4 - Mursaat Overseer":    {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W4 - Samarog":             {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Off Tank": 1}},
    "W4 - Deimos":              {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Hand Kite": 1}},
    # Wing 5 - Hall of Chains
    "W5 - Soulless Horror":     {"Tank": 2, "Heal": 2, "DPS": 6, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W5 - Dhuum":               {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Kite": 1}},
    # Wing 6 - Mythwright Gambit
    "W6 - Conjured Amalgamate": {"Tank": 0, "Heal": 2, "DPS": 8, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W6 - Twin Largos":         {"Tank": 2, "Heal": 2, "DPS": 6, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W6 - Qadim":               {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Kite": 1, "Lamps": 1, "Portals": 2}},
    # Wing 7 - Key of Ahdashim
    "W7 - Cardinal Adina":      {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W7 - Cardinal Sabir":      {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {}},
    "W7 - Qadim the Peerless":  {"Tank": 1, "Heal": 2, "DPS": 7, "boon_limits": {"Alacrity": 2, "Quickness": 2}, "special": {"Pylons": 3}},
}

WING_BOSSES = {
    "W1 - Spirit Vale":                ["W1 - Vale Guardian", "W1 - Gorseval", "W1 - Sabetha"],
    "W2 - Salvation Pass":             ["W2 - Slothasor", "W2 - Bandit Trio", "W2 - Matthias"],
    "W3 - Stronghold of the Faithful": ["W3 - Escort", "W3 - Keep Construct", "W3 - Xera"],
    "W4 - Bastion of the Penitent":    ["W4 - Cairn", "W4 - Mursaat Overseer", "W4 - Samarog", "W4 - Deimos"],
    "W5 - Hall of Chains":             ["W5 - Soulless Horror", "W5 - Dhuum"],
    "W6 - Mythwright Gambit":          ["W6 - Conjured Amalgamate", "W6 - Twin Largos", "W6 - Qadim"],
    "W7 - Key of Ahdashim":            ["W7 - Cardinal Adina", "W7 - Cardinal Sabir", "W7 - Qadim the Peerless"],
}

# ---------------------------------------------------------------------------
# Data layer
# ---------------------------------------------------------------------------

def _empty_data() -> dict:
    """Return a fresh, empty data structure."""
    return {
        'next_event_id': 1,
        'next_lottery_id': 1,
        'events': {},
        'players': {},
        'lotteries': {},
    }

def load_data() -> dict:
    """Load data from disk. Returns empty structure if file doesn't exist yet."""
    if not os.path.exists(DATA_FILE):
        return _empty_data()
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Warning: could not load data file ({e}). Starting fresh.")
        return _empty_data()

def save_data(data: dict) -> None:
    """Persist data to disk."""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)

def next_event_id(data: dict) -> str:
    """Claim and return the next event ID as a string, then increment the counter."""
    eid = str(data['next_event_id'])
    data['next_event_id'] += 1
    return eid

def next_lottery_id(data: dict) -> str:
    """Claim and return the next lottery ID as a string, then increment the counter."""
    lid = str(data['next_lottery_id'])
    data['next_lottery_id'] += 1
    return lid

# Datetimes are stored as UTC Unix timestamps (int) in JSON.
# Discord's <t:unix:F> format renders automatically in each viewer's local timezone.

def parse_utc_offset(offset_str: str) -> timedelta:
    """Parse a UTC offset string like 'UTC+1', 'UTC-5:30', '+2', '' into a timedelta."""
    s = offset_str.strip().upper().replace('UTC', '').replace('GMT', '').strip()
    if not s:
        return timedelta(0)
    sign = 1
    if s.startswith('+'):
        s = s[1:]
    elif s.startswith('-'):
        sign = -1
        s = s[1:]
    parts = s.split(':')
    try:
        hours   = int(parts[0]) if parts[0] else 0
        minutes = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        raise ValueError(f"Cannot parse UTC offset: {offset_str!r}")
    return sign * timedelta(hours=hours, minutes=minutes)

def dt_to_unix(dt: datetime) -> int:
    """Convert a UTC-aware datetime to a Unix timestamp for storage."""
    return int(dt.timestamp())

def unix_to_discord_ts(unix: int, style: str = 'F') -> str:
    """Return a Discord timestamp string that renders in the viewer's local timezone.
    Styles: F=full, f=short, D=date, T=time, R=relative, d=short date, t=short time.
    """
    return f"<t:{unix}:{style}>"

# ---------------------------------------------------------------------------
# Bot setup
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Event embed + signup views
# ---------------------------------------------------------------------------

ROLE_EMOJIS = {'Tank': '🛡️', 'Heal': '💚', 'DPS': '⚔️'}


def create_event_embed(event: dict, event_id: str) -> discord.Embed:
    """Build the public event embed shown in the channel."""
    title_emoji = '⚔️' if event['type'] == 'raid' else '🎮'
    ts          = event['unix_ts']
    # Discord renders <t:unix:F> in each viewer's local timezone automatically
    time_str    = f"{unix_to_discord_ts(ts, 'F')}  ({unix_to_discord_ts(ts, 'R')})"

    embed = discord.Embed(
        title=f"{title_emoji} {event['name']}",
        description=f"📅 {time_str}",
        color=0x2ecc71
    )
    if event.get('description'):
        embed.add_field(name="ℹ️ Info", value=event['description'], inline=False)

    participants = event.get('participants', {})

    for role in ['Tank', 'Heal', 'DPS']:
        limit = event['role_limits'].get(role, 0)
        if limit == 0:
            continue
        role_ps = [p for p in participants.values() if p['role'] == role]
        count   = len(role_ps)
        lines   = []
        for p in role_ps:
            boon_tag = f" [{p['boon']}]" if p.get('boon') else ""
            lines.append(f"{p['name']}{boon_tag}")
        embed.add_field(
            name=f"{ROLE_EMOJIS[role]} {role} ({count}/{limit})",
            value="\n".join(lines) if lines else "*(empty)*",
            inline=False
        )

    # Special roles — show individual numbered slots
    special_limits = event.get('special_role_limits', {})
    if any(v > 0 for v in special_limits.values()):
        special_lines = []
        for role, limit in special_limits.items():
            if limit == 0:
                continue
            filled = [p['name'] for p in participants.values() if p.get('special_role') == role]
            for i in range(limit):
                name = filled[i] if i < len(filled) else "*(empty)*"
                special_lines.append(f"**{role}** ({i+1}/{limit})  {name}")
        embed.add_field(name="🎯 Special Roles", value="\n".join(special_lines), inline=False)

    embed.set_footer(text=f"Event ID: {event_id}  •  {POINT_VALUES[event['type']]} points on attendance")
    return embed


async def _refresh_event_embed(event: dict, event_id: str) -> None:
    """Fetch the public message and edit it with the current embed."""
    channel = bot.get_channel(event['channel_id'])
    if not channel or not event.get('message_id'):
        return
    try:
        message = await channel.fetch_message(event['message_id'])
        await message.edit(embed=create_event_embed(event, event_id))
    except discord.NotFound:
        pass  # message was deleted — nothing to update


class EventView(discord.ui.View):
    """Persistent public signup view attached to the event embed."""
    def __init__(self, event_id: str):
        super().__init__(timeout=None)
        self.event_id = event_id

    @discord.ui.button(label="Register", style=discord.ButtonStyle.green, emoji="✅")
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return
        if event['status'] != 'open':
            await interaction.response.send_message("❌ This event is closed.", ephemeral=True)
            return
        await interaction.response.send_message(
            "**Select your role:**",
            view=RoleSelectView(self.event_id, event),
            ephemeral=True
        )

    @discord.ui.button(label="Leave Event", style=discord.ButtonStyle.red, emoji="❌")
    async def leave(self, interaction: discord.Interaction, button: discord.ui.Button):
        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.send_message("❌ Event not found.", ephemeral=True)
            return
        uid = str(interaction.user.id)
        if uid not in event.get('participants', {}):
            await interaction.response.send_message("You're not signed up for this event.", ephemeral=True)
            return
        del event['participants'][uid]
        save_data(data)
        await interaction.response.send_message("✅ You've left the event.", ephemeral=True)
        await _refresh_event_embed(event, self.event_id)


# --- Role select ---

class RoleSelectView(discord.ui.View):
    def __init__(self, event_id: str, event: dict):
        super().__init__(timeout=120)
        self.add_item(RoleSelect(event_id, event))


class RoleSelect(discord.ui.Select):
    def __init__(self, event_id: str, event: dict):
        self.event_id = event_id
        participants  = event.get('participants', {})
        options = []
        for role in ['Tank', 'Heal', 'DPS']:
            limit = event['role_limits'].get(role, 0)
            if limit == 0:
                continue
            count     = sum(1 for p in participants.values() if p['role'] == role)
            available = limit - count
            options.append(discord.SelectOption(
                label=f"{role} ({available} left)",
                value=role,
                emoji=ROLE_EMOJIS[role]
            ))
        super().__init__(placeholder="Choose your role...", options=options)

    async def callback(self, interaction: discord.Interaction):
        role = self.values[0]
        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.edit_message(content="❌ Event not found.", view=None)
            return

        # Re-check slot availability (could have filled since view was shown)
        count = sum(1 for p in event['participants'].values() if p['role'] == role)
        if count >= event['role_limits'].get(role, 0):
            await interaction.response.edit_message(
                content=f"❌ **{role}** is now full. Please choose a different role.",
                view=RoleSelectView(self.event_id, event)
            )
            return

        if role == 'Tank':
            # Tanks have no boon — sign up immediately
            uid = str(interaction.user.id)
            event['participants'][uid] = {
                'name': interaction.user.display_name,
                'role': 'Tank', 'boon': None, 'special_role': None
            }
            save_data(data)
            await interaction.response.edit_message(content="✅ Signed up as **Tank**!", view=None)
            await _refresh_event_embed(event, self.event_id)
        else:
            await interaction.response.edit_message(
                content=f"**{role}** selected. Now pick your boon:",
                view=BoonSelectView(self.event_id, role, event)
            )


# --- Boon select ---

class BoonSelectView(discord.ui.View):
    def __init__(self, event_id: str, role: str, event: dict):
        super().__init__(timeout=120)
        self.add_item(BoonSelect(event_id, role, event))


class BoonSelect(discord.ui.Select):
    def __init__(self, event_id: str, role: str, event: dict):
        self.event_id = event_id
        self.role     = role
        participants  = event.get('participants', {})
        boon_limits   = event.get('boon_limits', {})

        options = []
        for boon in ['Alacrity', 'Quickness', 'Condi']:
            cap = boon_limits.get(boon, 0)
            if cap == 0:
                continue
            if boon == 'Condi' and role != 'DPS':
                continue  # Condi is a DPS-only boon (Vale Guardian)
            filled    = sum(1 for p in participants.values() if p.get('boon') == boon)
            available = cap - filled
            if available > 0:
                options.append(discord.SelectOption(label=f"{boon} ({available} left)", value=boon))
            else:
                # Show as full so the player knows — selecting it triggers a soft error
                options.append(discord.SelectOption(
                    label=f"{boon} (FULL)", value=f"FULL_{boon}", description="This boon slot is full"
                ))
        options.append(discord.SelectOption(label="None", value="None", emoji="➖"))
        super().__init__(placeholder="Choose your boon...", options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value.startswith("FULL_"):
            data  = load_data()
            event = data['events'].get(self.event_id)
            await interaction.response.edit_message(
                content="❌ That boon is full. Please choose a different one.",
                view=BoonSelectView(self.event_id, self.role, event)
            )
            return

        boon  = None if value == "None" else value
        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.edit_message(content="❌ Event not found.", view=None)
            return

        special_limits = event.get('special_role_limits', {})
        has_special    = any(v > 0 for v in special_limits.values())

        if has_special:
            boon_txt = f" [{boon}]" if boon else ""
            await interaction.response.edit_message(
                content=f"**{self.role}{boon_txt}** selected. Pick a special role (optional):",
                view=SpecialRoleSelectView(self.event_id, self.role, boon, event)
            )
        else:
            uid = str(interaction.user.id)
            event['participants'][uid] = {
                'name': interaction.user.display_name,
                'role': self.role, 'boon': boon, 'special_role': None
            }
            save_data(data)
            boon_txt = f" [{boon}]" if boon else ""
            await interaction.response.edit_message(
                content=f"✅ Signed up as **{self.role}{boon_txt}**!", view=None
            )
            await _refresh_event_embed(event, self.event_id)


# --- Special role select ---

class SpecialRoleSelectView(discord.ui.View):
    def __init__(self, event_id: str, role: str, boon, event: dict):
        super().__init__(timeout=120)
        self.add_item(SpecialRoleSelect(event_id, role, boon, event))


class SpecialRoleSelect(discord.ui.Select):
    def __init__(self, event_id: str, role: str, boon, event: dict):
        self.event_id = event_id
        self.role     = role
        self.boon     = boon
        participants  = event.get('participants', {})
        special_limits = event.get('special_role_limits', {})

        options = [discord.SelectOption(label="None (no special role)", value="None", emoji="➖")]
        for special, limit in special_limits.items():
            if limit == 0:
                continue
            filled    = sum(1 for p in participants.values() if p.get('special_role') == special)
            available = limit - filled
            if available > 0:
                options.append(discord.SelectOption(label=f"{special} ({available} left)", value=special))
            else:
                options.append(discord.SelectOption(
                    label=f"{special} (FULL)", value=f"FULL_{special}", description="This slot is full"
                ))
        super().__init__(placeholder="Choose a special role (optional)...", options=options)

    async def callback(self, interaction: discord.Interaction):
        value = self.values[0]
        if value.startswith("FULL_"):
            data  = load_data()
            event = data['events'].get(self.event_id)
            await interaction.response.edit_message(
                content="❌ That special role slot is full. Please choose a different one.",
                view=SpecialRoleSelectView(self.event_id, self.role, self.boon, event)
            )
            return

        special_role = None if value == "None" else value
        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.edit_message(content="❌ Event not found.", view=None)
            return

        uid = str(interaction.user.id)
        event['participants'][uid] = {
            'name': interaction.user.display_name,
            'role': self.role, 'boon': self.boon, 'special_role': special_role
        }
        save_data(data)

        boon_txt    = f" [{self.boon}]" if self.boon else ""
        special_txt = f" — {special_role}" if special_role else ""
        await interaction.response.edit_message(
            content=f"✅ Signed up as **{self.role}{boon_txt}{special_txt}**!", view=None
        )
        await _refresh_event_embed(event, self.event_id)

# ---------------------------------------------------------------------------
# Event creation — /create_event
# ---------------------------------------------------------------------------

@bot.tree.command(name="create_event", description="Create a new event (officers only)")
async def create_event(interaction: discord.Interaction):
    await interaction.response.send_modal(EventSetupModal())


class EventSetupModal(discord.ui.Modal, title='Create Event'):
    event_name = discord.ui.TextInput(
        label='Event Name',
        placeholder='e.g. Tuesday Raid Night',
        max_length=100
    )
    description = discord.ui.TextInput(
        label='Description',
        placeholder='Optional details...',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    event_time = discord.ui.TextInput(
        label='Date & Time (your local time)',
        placeholder='YYYY-MM-DD HH:MM  (e.g. 2026-03-20 20:00)',
        max_length=16
    )
    timezone = discord.ui.TextInput(
        label='Your UTC offset',
        placeholder='e.g. UTC+1  UTC-5  UTC+5:30  UTC (for no offset)',
        default='UTC',
        max_length=10
    )

    async def on_submit(self, interaction: discord.Interaction):
        try:
            local_dt = datetime.strptime(self.event_time.value.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True
            )
            return

        try:
            offset  = parse_utc_offset(self.timezone.value)
            # Convert local time to UTC by subtracting the offset
            # e.g. 20:00 UTC+1 → 19:00 UTC
            utc_dt  = local_dt - offset
            unix_ts = dt_to_unix(utc_dt)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid UTC offset. Use format: UTC+1, UTC-5, UTC+5:30, or UTC.", ephemeral=True
            )
            return

        temp = {
            'name':        self.event_name.value.strip(),
            'description': self.description.value.strip(),
            'unix_ts':     unix_ts,     # stored as UTC Unix timestamp
            'channel_id':  interaction.channel.id,
        }
        embed = _creation_embed(temp, "Step 2 of 4: Select Wing")
        await interaction.response.send_message(embed=embed, view=WingSelectView(temp), ephemeral=True)


class WingSelectView(discord.ui.View):
    def __init__(self, temp: dict):
        super().__init__(timeout=300)
        self.add_item(WingSelect(temp))


class WingSelect(discord.ui.Select):
    def __init__(self, temp: dict):
        self.temp = temp
        options = [
            discord.SelectOption(label="W1 - Spirit Vale",                emoji="⚔️"),
            discord.SelectOption(label="W2 - Salvation Pass",             emoji="⚔️"),
            discord.SelectOption(label="W3 - Stronghold of the Faithful", emoji="⚔️"),
            discord.SelectOption(label="W4 - Bastion of the Penitent",    emoji="⚔️"),
            discord.SelectOption(label="W5 - Hall of Chains",             emoji="⚔️"),
            discord.SelectOption(label="W6 - Mythwright Gambit",          emoji="⚔️"),
            discord.SelectOption(label="W7 - Key of Ahdashim",            emoji="⚔️"),
            discord.SelectOption(label="Other (Fractals, WvW, etc.)",     emoji="🎮", value="Other"),
        ]
        super().__init__(placeholder="Select a wing or Other...", options=options)

    async def callback(self, interaction: discord.Interaction):
        selected = self.values[0]
        self.temp['wing'] = selected

        if selected == "Other":
            self.temp['type'] = 'normal'
            self.temp['boss'] = None
            embed = _creation_embed(self.temp, "Step 3 of 4: Set Role Slots")
            await interaction.response.edit_message(embed=embed, view=OtherRolesView(self.temp))
        else:
            self.temp['type'] = 'raid'
            bosses = WING_BOSSES[selected]
            embed = _creation_embed(self.temp, f"Step 3 of 4: Select Boss ({selected})")
            await interaction.response.edit_message(embed=embed, view=BossSelectView(self.temp, bosses))


class BossSelectView(discord.ui.View):
    def __init__(self, temp: dict, bosses: list):
        super().__init__(timeout=300)
        self.add_item(BossSelect(temp, bosses))


class BossSelect(discord.ui.Select):
    def __init__(self, temp: dict, bosses: list):
        self.temp = temp
        options = [discord.SelectOption(label=b) for b in bosses]
        super().__init__(placeholder="Select a boss...", options=options)

    async def callback(self, interaction: discord.Interaction):
        boss = self.values[0]
        self.temp['boss'] = boss
        tmpl = BOSS_TEMPLATES[boss]

        # Pull slot counts and boon limits directly from the template
        self.temp['role_limits'] = {
            'Tank': tmpl['Tank'],
            'Heal': tmpl['Heal'],
            'DPS':  tmpl['DPS'],
        }
        self.temp['boon_limits']        = dict(tmpl['boon_limits'])
        self.temp['special_role_limits'] = dict(tmpl['special'])

        embed = _role_review_embed(self.temp)
        await interaction.response.edit_message(embed=embed, view=RoleReviewView(self.temp))


# ---------------------------------------------------------------------------
# Other (non-raid) path — manual role slot entry
# ---------------------------------------------------------------------------

class OtherRolesView(discord.ui.View):
    def __init__(self, temp: dict):
        super().__init__(timeout=300)
        self.temp = temp

    @discord.ui.button(label="Set Role Slots", style=discord.ButtonStyle.blurple)
    async def set_roles(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(OtherRolesModal(self.temp, self))

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelled.", embed=None, view=None)


class OtherRolesModal(discord.ui.Modal, title='Set Role Slots'):
    def __init__(self, temp: dict, parent_view: OtherRolesView):
        super().__init__()
        self.temp = temp
        self.parent_view = parent_view

    tank_count = discord.ui.TextInput(label='Tank slots (0–2)',  default='0', max_length=1)
    heal_count = discord.ui.TextInput(label='Heal slots (1–5)',  default='2', max_length=1)
    dps_count  = discord.ui.TextInput(label='DPS slots (1–20)', default='8', max_length=2)

    async def on_submit(self, interaction: discord.Interaction):
        try:
            tank = int(self.tank_count.value)
            heal = int(self.heal_count.value)
            dps  = int(self.dps_count.value)
            if any(v < 0 for v in [tank, heal, dps]) or (heal + dps) == 0:
                raise ValueError
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid slot counts. Heal + DPS must be at least 1.", ephemeral=True
            )
            return

        self.temp['role_limits']         = {'Tank': tank, 'Heal': heal, 'DPS': dps}
        self.temp['boon_limits']         = {'Alacrity': 2, 'Quickness': 2}
        self.temp['special_role_limits'] = {}

        embed = _role_review_embed(self.temp)
        await interaction.response.edit_message(embed=embed, view=RoleReviewView(self.temp))


# ---------------------------------------------------------------------------
# Role review — shared final step before posting
# ---------------------------------------------------------------------------

class RoleReviewView(discord.ui.View):
    def __init__(self, temp: dict):
        super().__init__(timeout=300)
        self.temp = temp

    @discord.ui.button(label="✅ Confirm & Post", style=discord.ButtonStyle.green)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        await _post_event(interaction, self.temp)

    @discord.ui.button(label="❌ Cancel", style=discord.ButtonStyle.red)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="❌ Cancelled.", embed=None, view=None)


async def _post_event(interaction: discord.Interaction, temp: dict):
    """Finalise the event, save it, and post the embed to the channel."""
    data = load_data()
    eid  = next_event_id(data)

    event = {
        'name':                temp['name'],
        'description':         temp['description'],
        'unix_ts':             temp['unix_ts'],        # UTC Unix timestamp
        'type':                temp['type'],           # 'raid' | 'normal'
        'boss':                temp.get('boss'),
        'wing':                temp.get('wing'),
        'role_limits':         temp['role_limits'],
        'boon_limits':         temp['boon_limits'],
        'special_role_limits': temp['special_role_limits'],
        'participants':        {},
        'channel_id':          temp['channel_id'],
        'message_id':          None,
        'status':              'open',
        'reminded_1h':         False,
        'reminded_30m':        False,
        'point_value':         POINT_VALUES[temp['type']],
    }
    data['events'][eid] = event
    save_data(data)

    embed   = create_event_embed(event, eid)
    view    = EventView(eid)
    channel = interaction.channel
    message = await channel.send(embed=embed, view=view)

    # Store message ID so we can edit the embed later
    data['events'][eid]['message_id'] = message.id
    save_data(data)

    await interaction.response.edit_message(
        content=f"✅ Event **{event['name']}** posted! (ID: {eid})",
        embed=None, view=None
    )


# ---------------------------------------------------------------------------
# Creation flow helper embeds
# ---------------------------------------------------------------------------

def _creation_embed(temp: dict, step_title: str) -> discord.Embed:
    """Ephemeral status embed shown during the creation wizard."""
    if 'unix_ts' in temp:
        time_display = unix_to_discord_ts(temp['unix_ts'], 'F')
    else:
        time_display = "*(not set)*"
    lines = [
        f"**Name:** {temp['name']}",
        f"**Time:** {time_display}",
    ]
    if temp.get('description'):
        lines.append(f"**Description:** {temp['description']}")
    if temp.get('wing'):
        lines.append(f"**Wing:** {temp['wing']}")
    if temp.get('boss'):
        lines.append(f"**Boss:** {temp['boss']}")
    return discord.Embed(title=step_title, description="\n".join(lines), color=0x0099ff)


def _role_review_embed(temp: dict) -> discord.Embed:
    """Show the pre-filled role slots for officer review before posting."""
    embed = _creation_embed(temp, "Step 4 of 4: Review & Confirm")

    role_emojis = {'Tank': '🛡️', 'Heal': '💚', 'DPS': '⚔️'}
    slots_lines = []
    for role, count in temp['role_limits'].items():
        if count > 0:
            slots_lines.append(f"{role_emojis[role]} {role}: {count} slot{'s' if count != 1 else ''}")

    boon_lines = [f"{boon} ×{cap}" for boon, cap in temp['boon_limits'].items()]

    special_lines = [
        f"• {role}: {count}" for role, count in temp['special_role_limits'].items() if count > 0
    ]

    embed.add_field(name="Role Slots", value="\n".join(slots_lines) or "None", inline=True)
    embed.add_field(name="Boon Limits", value="\n".join(boon_lines), inline=True)
    if special_lines:
        embed.add_field(name="Special Roles", value="\n".join(special_lines), inline=False)

    ticket_val = POINT_VALUES[temp['type']]
    embed.set_footer(text=f"Attendance reward: {ticket_val} points")
    return embed

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    bot.start_time = datetime.now()
    print(f'{bot.user} is online!')

    if not check_events.is_running():
        check_events.start()

    print("Syncing commands...")
    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s): {[c.name for c in synced]}")
    except Exception as e:
        print(f"Failed to sync commands: {e}")

# ---------------------------------------------------------------------------
# Admin commands
# ---------------------------------------------------------------------------

def _is_officer(interaction: discord.Interaction) -> bool:
    """True if the user has Manage Events or Administrator permission."""
    perms = interaction.user.guild_permissions
    return perms.manage_events or perms.administrator


@bot.tree.command(name="delete_event", description="Delete an event and remove its Discord message (officers only)")
async def delete_event(interaction: discord.Interaction, event_id: str):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return

    data  = load_data()
    event = data['events'].get(event_id)
    if not event:
        await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
        return

    # Delete the public Discord message if we can find it
    channel = bot.get_channel(event['channel_id'])
    if channel and event.get('message_id'):
        try:
            message = await channel.fetch_message(event['message_id'])
            await message.delete()
        except discord.NotFound:
            pass

    del data['events'][event_id]
    save_data(data)
    await interaction.response.send_message(f"✅ Event `{event_id}` deleted.", ephemeral=True)


@bot.tree.command(name="edit_event", description="Edit event name, description, or time (officers only)")
async def edit_event(interaction: discord.Interaction, event_id: str):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return

    data  = load_data()
    event = data['events'].get(event_id)
    if not event:
        await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
        return

    await interaction.response.send_modal(EditEventModal(event_id, event))


class EditEventModal(discord.ui.Modal, title='Edit Event'):
    event_name = discord.ui.TextInput(label='Event Name', max_length=100)
    description = discord.ui.TextInput(
        label='Description',
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=500
    )
    event_time = discord.ui.TextInput(
        label='New Date & Time (your local time)',
        placeholder='YYYY-MM-DD HH:MM',
        max_length=16
    )
    timezone = discord.ui.TextInput(
        label='Your UTC offset',
        placeholder='e.g. UTC+1  UTC-5  UTC (leave as UTC if unchanged)',
        default='UTC',
        max_length=10
    )

    def __init__(self, event_id: str, event: dict):
        super().__init__()
        self.event_id = event_id
        # Pre-fill time as UTC so officer knows the current stored value
        utc_dt = datetime.utcfromtimestamp(event['unix_ts'])
        self.event_name.default  = event['name']
        self.description.default = event.get('description', '')
        self.event_time.default  = utc_dt.strftime('%Y-%m-%d %H:%M')

    async def on_submit(self, interaction: discord.Interaction):
        try:
            local_dt = datetime.strptime(self.event_time.value.strip(), "%Y-%m-%d %H:%M")
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid time format. Use: YYYY-MM-DD HH:MM", ephemeral=True
            )
            return

        try:
            offset  = parse_utc_offset(self.timezone.value)
            unix_ts = dt_to_unix(local_dt - offset)
        except ValueError:
            await interaction.response.send_message(
                "❌ Invalid UTC offset. Use format: UTC+1, UTC-5, or UTC.", ephemeral=True
            )
            return

        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.send_message("❌ Event no longer exists.", ephemeral=True)
            return

        event['name']        = self.event_name.value.strip()
        event['description'] = self.description.value.strip()
        event['unix_ts']     = unix_ts
        # Reset reminder flags so they fire again at the new time
        event['reminded_1h']  = False
        event['reminded_30m'] = False
        save_data(data)

        await _refresh_event_embed(event, self.event_id)
        await interaction.response.send_message(f"✅ Event `{self.event_id}` updated.", ephemeral=True)


@bot.tree.command(name="add_attendee", description="Add a filler who attended but didn't sign up (officers only)")
async def add_attendee(interaction: discord.Interaction, event_id: str, user: discord.Member):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return

    data  = load_data()
    event = data['events'].get(event_id)
    if not event:
        await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
        return

    uid = str(user.id)
    if uid in event['participants']:
        await interaction.response.send_message(
            f"❌ {user.display_name} is already on the roster.", ephemeral=True
        )
        return

    event['participants'][uid] = {
        'name': interaction.guild.get_member(user.id).display_name if interaction.guild else user.display_name,
        'role': 'Filler', 'boon': None, 'special_role': None,
    }
    save_data(data)
    await _refresh_event_embed(event, event_id)
    await interaction.response.send_message(
        f"✅ Added **{user.display_name}** as a filler to event `{event_id}`.", ephemeral=True
    )


@bot.tree.command(name="close_event", description="Close event and confirm who attended (officers only)")
async def close_event(interaction: discord.Interaction, event_id: str):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return

    data  = load_data()
    event = data['events'].get(event_id)
    if not event:
        await interaction.response.send_message(f"❌ Event `{event_id}` not found.", ephemeral=True)
        return
    if event['status'] != 'open':
        await interaction.response.send_message(f"❌ Event `{event_id}` is already closed.", ephemeral=True)
        return

    participants = event.get('participants', {})
    if not participants:
        event['status'] = 'closed'
        save_data(data)
        await interaction.response.send_message(
            f"✅ Event `{event_id}` closed. No participants — no points awarded.", ephemeral=True
        )
        return

    embed = discord.Embed(
        title=f"Close: {event['name']}",
        description=(
            "Select everyone who **actually attended**.\n"
            f"Each confirmed player receives **{event['point_value']} points**."
        ),
        color=0xf39c12
    )
    await interaction.response.send_message(
        embed=embed, view=AttendanceConfirmView(event_id, event), ephemeral=True
    )


class AttendanceConfirmView(discord.ui.View):
    def __init__(self, event_id: str, event: dict):
        super().__init__(timeout=300)
        self.event_id      = event_id
        self.confirmed_uids = []           # populated by AttendanceSelect.callback
        self.add_item(AttendanceSelect(event_id, event))

    @discord.ui.button(label="Confirm & Award Points", style=discord.ButtonStyle.green, emoji="✅", row=1)
    async def confirm(self, interaction: discord.Interaction, button: discord.ui.Button):
        confirmed_uids = self.confirmed_uids

        data  = load_data()
        event = data['events'].get(self.event_id)
        if not event:
            await interaction.response.edit_message(content="❌ Event not found.", embed=None, view=None)
            return

        point_value = event['point_value']
        awarded = []
        for uid in confirmed_uids:
            participant = event['participants'].get(uid)
            if not participant:
                continue
            name = participant['name']
            if uid not in data['players']:
                data['players'][uid] = {'name': name, 'points': 0, 'events_attended': 0}
            data['players'][uid]['name']            = name   # keep display name current
            data['players'][uid]['points']          += point_value
            data['players'][uid]['events_attended'] += 1
            awarded.append(name)

        event['status'] = 'closed'
        save_data(data)

        if awarded:
            names_text  = "\n".join(f"• {n}" for n in awarded)
            result_text = f"✅ **Event closed.** {point_value} points awarded to:\n{names_text}"
        else:
            result_text = "✅ **Event closed.** No attendance confirmed — no points awarded."

        await interaction.response.edit_message(content=result_text, embed=None, view=None)

    @discord.ui.button(label="Cancel", style=discord.ButtonStyle.grey, emoji="❌", row=1)
    async def cancel(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.edit_message(content="Cancelled.", embed=None, view=None)


class AttendanceSelect(discord.ui.Select):
    def __init__(self, event_id: str, event: dict):
        self.event_id    = event_id
        participants     = event.get('participants', {})
        point_value     = event['point_value']

        options = [
            discord.SelectOption(
                label=p['name'][:100],
                value=uid,
                description=p['role'] + (f" [{p['boon']}]" if p.get('boon') else "")
            )
            for uid, p in participants.items()
        ]
        super().__init__(
            placeholder="Select who attended...",
            options=options,
            min_values=0,
            max_values=len(options),
            row=0
        )
        self.point_value = point_value

    async def callback(self, interaction: discord.Interaction):
        # Store selected UIDs on the parent view for the Confirm button to read
        self.view.confirmed_uids = self.values

        # Show a live preview of who will receive points
        if self.values:
            data  = load_data()
            event = data['events'].get(self.event_id)
            names = [
                event['participants'][uid]['name']
                for uid in self.values
                if uid in event.get('participants', {})
            ]
            preview = "\n".join(f"• {n}" for n in names)
        else:
            preview = "*(none selected)*"

        embed = discord.Embed(
            title="Attendance Preview",
            description=(
                f"**Will receive {self.point_value} points:**\n{preview}\n\n"
                "Click **Confirm & Award Points** when ready."
            ),
            color=0xf39c12
        )
        await interaction.response.edit_message(embed=embed)


# ---------------------------------------------------------------------------
# Reminder loop
# ---------------------------------------------------------------------------

@tasks.loop(minutes=1)
async def check_events():
    """Send 1h and 30m reminders for upcoming events."""
    data = load_data()
    now = datetime.now()

    changed = False
    for eid, event in data['events'].items():
        if event.get('status') != 'open':
            continue

        event_unix = event['unix_ts']
        now_unix   = int(now.timestamp())
        channel    = bot.get_channel(event['channel_id'])
        if not channel:
            continue

        if not event.get('reminded_1h') and now_unix >= event_unix - 3600:
            await _send_reminder(channel, event, "1 hour")
            event['reminded_1h'] = True
            changed = True

        if not event.get('reminded_30m') and now_unix >= event_unix - 1800:
            await _send_reminder(channel, event, "30 minutes")
            event['reminded_30m'] = True
            changed = True

    if changed:
        save_data(data)

async def _send_reminder(channel, event: dict, time_left: str):
    participants = event.get('participants', {})
    if not participants:
        return
    mentions = " ".join(f"<@{uid}>" for uid in participants)
    embed = discord.Embed(
        title=f"⏰ Reminder: {event['name']}",
        description=f"Starting in {time_left}!",
        color=0xff9900
    )
    await channel.send(mentions, embed=embed)

# ---------------------------------------------------------------------------
# Lottery system
# ---------------------------------------------------------------------------

@bot.tree.command(name="create_lottery", description="Create a new points lottery (officers only)")
async def create_lottery(interaction: discord.Interaction):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return
    await interaction.response.send_modal(CreateLotteryModal())


class CreateLotteryModal(discord.ui.Modal, title='Create Lottery'):
    lottery_name = discord.ui.TextInput(
        label='Lottery Name',
        placeholder='e.g. March 2026 Lottery',
        max_length=100
    )
    prizes = discord.ui.TextInput(
        label='Prizes (one per line, best prize first)',
        placeholder='500g\n250g\nLegendary weapon skin',
        style=discord.TextStyle.paragraph,
        max_length=1000
    )

    async def on_submit(self, interaction: discord.Interaction):
        prize_list = [p.strip() for p in self.prizes.value.strip().splitlines() if p.strip()]
        if not prize_list:
            await interaction.response.send_message("❌ At least one prize is required.", ephemeral=True)
            return

        data = load_data()
        lid  = next_lottery_id(data)
        data['lotteries'][lid] = {
            'name':    self.lottery_name.value.strip(),
            'prizes':  prize_list,
            'status':  'open',
            'winners': []
        }
        save_data(data)

        prizes_display = "\n".join(f"{i+1}. {p}" for i, p in enumerate(prize_list))
        await interaction.response.send_message(
            f"✅ Lottery **{self.lottery_name.value.strip()}** created (ID: `{lid}`).\n\n**Prizes:**\n{prizes_display}",
            ephemeral=True
        )


@bot.tree.command(name="draw_lottery", description="Draw lottery winners and reset all points (officers only)")
async def draw_lottery(interaction: discord.Interaction, lottery_id: str):
    if not _is_officer(interaction):
        await interaction.response.send_message("❌ Officers only.", ephemeral=True)
        return

    data    = load_data()
    lottery = data['lotteries'].get(lottery_id)
    if not lottery:
        await interaction.response.send_message(f"❌ Lottery `{lottery_id}` not found.", ephemeral=True)
        return
    if lottery['status'] == 'drawn':
        await interaction.response.send_message(f"❌ Lottery `{lottery_id}` has already been drawn.", ephemeral=True)
        return

    # Build the weighted draw pool — more points = more chances
    pool    = [(uid, p) for uid, p in data['players'].items() if p['points'] > 0]
    if not pool:
        await interaction.response.send_message("❌ No players have points yet — cannot draw.", ephemeral=True)
        return

    weights = [p['points'] for _, p in pool]
    winners = []

    for prize in lottery['prizes']:
        if not pool:
            break
        # Pick one winner from the remaining pool, weighted by points
        idx              = random.choices(range(len(pool)), weights=weights, k=1)[0]
        winner_uid, winner_data = pool[idx]
        winners.append({'uid': winner_uid, 'name': winner_data['name'], 'prize': prize})
        # Remove winner so they can't win a second prize
        pool.pop(idx)
        weights.pop(idx)

    # Persist results and reset all points
    lottery['status']  = 'drawn'
    lottery['winners'] = winners
    for uid in data['players']:
        data['players'][uid]['points'] = 0
    save_data(data)

    # Public announcement embed
    medals = {1: '🥇', 2: '🥈', 3: '🥉'}
    lines  = [
        f"{medals.get(i, f'**{i}.**')} <@{w['uid']}> — **{w['prize']}**"
        for i, w in enumerate(winners, start=1)
    ]
    embed = discord.Embed(
        title=f"🎉 {lottery['name']} — Results!",
        description="\n".join(lines) if lines else "No eligible players.",
        color=0xf1c40f
    )
    embed.set_footer(text="All points have been reset to 0. Good luck next time!")
    await interaction.response.send_message(embed=embed)


# ---------------------------------------------------------------------------
# Utility commands
# ---------------------------------------------------------------------------

@bot.tree.command(name="list_events", description="Show all open events")
async def list_events(interaction: discord.Interaction):
    data   = load_data()
    now_ts = int(datetime.utcnow().timestamp())
    open_events = {
        eid: e for eid, e in data['events'].items()
        if e.get('status') == 'open'
    }

    if not open_events:
        await interaction.response.send_message("No open events right now.", ephemeral=True)
        return

    embed = discord.Embed(title="📅 Open Events", color=0x0099ff)
    for eid, e in open_events.items():
        ts         = e['unix_ts']
        signed_up  = len(e.get('participants', {}))
        total_slots = sum(e['role_limits'].values())
        boss_line  = f"**Boss:** {e['boss']}\n" if e.get('boss') else ""
        embed.add_field(
            name=f"{e['name']}  (ID: {eid})",
            value=(
                f"{boss_line}"
                f"**When:** {unix_to_discord_ts(ts, 'F')}\n"
                f"**Signed up:** {signed_up}/{total_slots}"
            ),
            inline=False
        )

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="leaderboard", description="Show the points leaderboard")
async def leaderboard(interaction: discord.Interaction):
    data    = load_data()
    players = data.get('players', {})

    if not players:
        await interaction.response.send_message("No points recorded yet.", ephemeral=True)
        return

    sorted_players = sorted(players.values(), key=lambda p: p['points'], reverse=True)

    embed = discord.Embed(title="🏆 Points Leaderboard", color=0xf1c40f)
    medals = {1: "🥇", 2: "🥈", 3: "🥉"}
    lines  = []
    for i, p in enumerate(sorted_players[:15], start=1):
        prefix = medals.get(i, f"`{i}.`")
        lines.append(f"{prefix} **{p['name']}** — {p['points']} pts  *(attended {p['events_attended']})*")

    embed.description = "\n".join(lines)
    await interaction.response.send_message(embed=embed)


@bot.tree.command(name="my_points", description="Check your own point total (private)")
async def my_points(interaction: discord.Interaction):
    data   = load_data()
    uid    = str(interaction.user.id)
    player = data['players'].get(uid)

    if not player:
        await interaction.response.send_message(
            "You don't have any points yet — attend an event to earn some!", ephemeral=True
        )
        return

    embed = discord.Embed(
        title="📊 Your Points",
        description=(
            f"**Points:** {player['points']}\n"
            f"**Events attended:** {player['events_attended']}"
        ),
        color=0x2ecc71
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="status", description="Show bot status and uptime")
async def status_command(interaction: discord.Interaction):
    data     = load_data()
    now      = datetime.utcnow()
    now_unix = int(now.timestamp())
    uptime   = now - bot.start_time
    h, rem   = divmod(int(uptime.total_seconds()), 3600)
    m, s     = divmod(rem, 60)

    total_events    = len(data['events'])
    upcoming_events = sum(
        1 for e in data['events'].values()
        if e.get('status') == 'open' and e['unix_ts'] > now_unix
    )
    total_players = len(data['players'])

    embed = discord.Embed(title="📡 KDS Bot Status", color=0x00ff00)
    embed.add_field(name="🟢 Status",   value="Online",                          inline=True)
    embed.add_field(name="⏱ Uptime",   value=f"{h}h {m}m {s}s",                inline=True)
    embed.add_field(name="📅 Events",   value=f"Upcoming: {upcoming_events}  •  Total: {total_events}", inline=False)
    embed.add_field(name="👥 Players",  value=str(total_players),               inline=True)
    embed.add_field(name="⏰ Reminders", value="Running ✅" if check_events.is_running() else "Stopped ❌", inline=True)

    await interaction.response.send_message(embed=embed, ephemeral=True)


@bot.tree.command(name="help", description="Show available commands")
async def help_command(interaction: discord.Interaction):
    embed = discord.Embed(
        title="❓ KDS Bot Help",
        description="Guild Wars 2 raid event management and points tracking.",
        color=0x0099ff
    )
    embed.add_field(
        name="📅 Events",
        value=(
            "**/create_event** — Create a new event (officers)\n"
            "**/list_events** — Show all open events\n"
            "**/edit_event `<id>`** — Edit name, description, or time (officers)\n"
            "**/delete_event `<id>`** — Delete an event (officers)\n"
            "**/close_event `<id>`** — Confirm attendance and award points (officers)\n"
            "**/add_attendee `<id>` `<user>`** — Add a filler to the roster (officers)"
        ),
        inline=False
    )
    embed.add_field(
        name="🎯 Signing Up",
        value=(
            "Click **Register** on an event embed to sign up\n"
            "Select your role → boon → special role (if applicable)\n"
            "Click **Leave Event** to remove yourself"
        ),
        inline=False
    )
    embed.add_field(
        name="🏆 Points",
        value=(
            "**/leaderboard** — Show top players by points\n"
            "**/my_points** — Check your own total (private)"
        ),
        inline=False
    )
    embed.add_field(
        name="ℹ️ Other",
        value="**/status** — Bot uptime and stats",
        inline=False
    )
    await interaction.response.send_message(embed=embed, ephemeral=True)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    print("Starting KDS Bot...")
    start_server()
    print("Starting Discord bot...")
    bot.run(os.getenv('BOT_TOKEN'))
