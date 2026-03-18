# KDS Bot

A Discord bot for the KDS Guild Wars 2 guild. Manages raid and guild event creation, player signups, attendance tracking, and a points-based lottery system.

## Features

- **Event creation wizard** — step-by-step slash command to create events with role/boon slot pre-filling based on boss templates
- **Public signup flow** — players register with role (Tank/Heal/DPS), boon (Alacrity/Quickness), and optional special roles
- **Attendance confirmation** — 2 hours after an event starts, the creator receives a DM to confirm who attended and award points automatically
- **Points system** — raid events award 20 pts, guild missions award 10 pts
- **Lottery system** — weighted random draw by points balance, resets all points after draw
- **Event reminders** — automatic channel reminders at 1 hour and 30 minutes before start

## Event Types

| Type | Points | Signup |
|------|--------|--------|
| Raid (W1–W7) | 20 | Role + boon + special roles |
| Fractals | 0 | Role + boon (1 Heal, 4 DPS) |
| Guild Missions | 10 | Open (attendee list) |
| Hang Out / Other Games | 0 | Open (attendee list) |
| Other | 10 | Manual role slots |

## Commands

### Officer Commands
| Command | Description |
|---------|-------------|
| `/create_event` | Open the event creation wizard |
| `/edit_event <id>` | Edit an event's name, description, or time |
| `/delete_event <id>` | Delete an event and remove its Discord message |
| `/close_event <id>` | Manually close an event and confirm attendance |
| `/add_attendee <id> <user>` | Add a filler who attended but didn't sign up |
| `/create_lottery` | Create a new points lottery |
| `/draw_lottery <id>` | Draw lottery winners and reset all points |

### Player Commands
| Command | Description |
|---------|-------------|
| `/list_events` | Show all open events |
| `/my_points` | Check your own point total |
| `/leaderboard` | Show the guild points leaderboard |
| `/status` | Show bot status and uptime |
| `/help` | Show available commands |

## Tech Stack

- **Language:** Python 3.13
- **Library:** discord.py 2.5.2
- **Persistence:** JSON file on Railway Volume (`/data/kds_bot_data.json`)
- **Hosting:** Railway

## Setup

### Environment Variables
| Variable | Description |
|----------|-------------|
| `DISCORD_TOKEN` | Your bot token from the Discord Developer Portal |
| `PORT` | HTTP port for Railway keepalive (set automatically by Railway) |

### Running Locally
```bash
pip install -r requirements.txt
DISCORD_TOKEN=your_token_here python raid_bot.py
```

### Deploying to Railway
1. Push to GitHub
2. Connect the repo in Railway
3. Add a Volume mounted at `/data`
4. Set the `DISCORD_TOKEN` environment variable
5. Railway will auto-deploy on every push to `main`

## Points & Lottery

- Players earn points when an officer confirms their attendance after an event
- The bot automatically DMs the event creator 2 hours after start to confirm attendance
- `/draw_lottery` performs a weighted random draw — players with more points have a higher chance of winning
- All points reset to 0 after a lottery draw
