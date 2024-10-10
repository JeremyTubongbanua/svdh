#!/usr/bin/env python3

import os
import discord
from discord.ext import tasks
import datetime
import requests
import pytz
import re
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv('BOT_TOKEN')
BREAKFAST_CHANNEL_ID = int(os.getenv('SVDH_BREAKFAST'))
LUNCH_CHANNEL_ID = int(os.getenv('SVDH_LUNCH'))
DINNER_CHANNEL_ID = int(os.getenv('SVDH_DINNER'))

CATEGORY_ALIASES = {
    'The Kitchen': 'Main Course Meat Station',
    'Grill House': 'Fried Food and Burgers Station',
    'Global Eats': 'Pasta Station',
    'The Sprout': 'Vegetarian Station',
    'Create': 'DIY but not DIY station',
    'My Pantry': 'DIY Station',
    'Al Forno': 'Pizza',
    'Leaf Market': 'Salad Bar',
    'Spoons and Ladles': 'Soups',
    'Hydration': 'Drinks',
    'Sweet Treats': 'Desserts and Fresh Fruit',
}

CATEGORY_EMOJIS = {
    'The Kitchen': '🍖',
    'Grill House': '🍔',
    'Global Eats': '🍝',
    'The Sprout': '🥗',
    'Create': '🍲',
    'My Pantry': '🥣',
    'Al Forno': '🍕',
    'Leaf Market': '🥬',
    'Spoons and Ladles': '🍜',
    'Hydration': '🥤',
    'Sweet Treats': '🍰',
}

BRUH_CATEGORIES = [
    'Al Forno',
    'Leaf Market',
    'Spoons and Ladles',
    'Hydration',
    'Sweet Treats',
]

POSTED_TRACK_FILE = "already_posted.txt"

EMOJIS = {
    'breakfast': '☕️🥐🍳',
    'lunch': '🍔🥗🍜',
    'dinner': '🍽️🍝🥩',
}

def get_initial_data(date_str):
    url = 'https://api.dineoncampus.ca/v1/location/63f8f1a992d6b40415c69179/periods'
    params = {'platform': '0', 'date': date_str}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except ValueError:
        print("Error parsing JSON response")
        return None

def get_meal_data(period_id, date_str):
    url = f'https://api.dineoncampus.ca/v1/location/63f8f1a992d6b40415c69179/periods/{period_id}'
    params = {'platform': '0', 'date': date_str}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        return None
    except ValueError:
        print("Error parsing JSON response")
        return None

def get_menu(meal_name, date_str, more=False):
    meal_name = meal_name.lower()
    data = get_initial_data(date_str)
    if data is None:
        return None

    periods = data.get('periods', [])

    period_id = None
    for period in periods:
        if period['name'].lower() == meal_name:
            period_id = period['id']
            break

    if not period_id:
        print(f"No data found for {meal_name} on {date_str}")
        return None

    meal_data = get_meal_data(period_id, date_str)
    if meal_data is None:
        return None

    categories = meal_data.get('menu', {}).get('periods', {}).get('categories', [])

    if not categories:
        print(f"No menu data available for {meal_name} on {date_str}")
        return None

    menu_lines = []
    for category in categories:
        if not more and category['name'] in BRUH_CATEGORIES:
            continue
        # Fetch emoji for category if available
        emoji = CATEGORY_EMOJIS.get(category['name'], '')
        category_name = CATEGORY_ALIASES.get(category['name'], category['name'])
        menu_lines.append(f"{emoji} **{category_name}**")
        for item in category.get('items', []):
            menu_lines.append(f"- {item['name']}")
        menu_lines.append('')
    return '\n'.join(menu_lines)

def has_already_posted(date_str):
    if not os.path.exists(POSTED_TRACK_FILE):
        return False
    with open(POSTED_TRACK_FILE, 'r') as file:
        posted_dates = file.read().splitlines()
    return date_str in posted_dates

def mark_as_posted(date_str):
    with open(POSTED_TRACK_FILE, 'a') as file:
        file.write(f"{date_str}\n")

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

@tasks.loop(minutes=1)
async def daily_menu():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    today_str = now.strftime('%Y-%m-%d')
    yesterday_str = (now - datetime.timedelta(days=1)).strftime('%Y-%m-%d')

    if now.hour == 6 and now.minute == 0:
        if not has_already_posted(yesterday_str):
            await post_meals(yesterday_str)
            mark_as_posted(yesterday_str)
        if not has_already_posted(today_str):
            await post_meals(today_str)
            mark_as_posted(today_str)

async def post_meals(date_str):
    meals = {
        'breakfast': BREAKFAST_CHANNEL_ID,
        'lunch': LUNCH_CHANNEL_ID,
        'dinner': DINNER_CHANNEL_ID
    }
    formatted_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').strftime('%B %d, %Y')

    for meal, channel_id in meals.items():
        menu = get_menu(meal, date_str)
        if menu:
            channel = bot.get_channel(channel_id)
            if channel is None:
                print(f"Channel with ID {channel_id} not found.")
                continue
            emoji = EMOJIS.get(meal, '')
            embed = discord.Embed(
                title=f"{emoji} {meal.capitalize()} Menu for {formatted_date}",
                description=menu,
                color=0x1D82B6
            )
            await channel.send(embed=embed)

@daily_menu.before_loop
async def before_daily_menu():
    await bot.wait_until_ready()

def check_posted_file():
    if not os.path.exists(POSTED_TRACK_FILE) or os.path.getsize(POSTED_TRACK_FILE) == 0:
        with open(POSTED_TRACK_FILE, 'a') as file:
            file.write("# File initialized on startup\n")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    check_posted_file()
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    today_str = now.strftime('%Y-%m-%d')
    if not has_already_posted(today_str):
        await post_meals(today_str)
        mark_as_posted(today_str)
    if not daily_menu.is_running():
        daily_menu.start()
    await tree.sync()

@tree.command(name="force", description="Force post the meals for a specified date")
async def force(interaction: discord.Interaction, date_input: str):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    match = re.match(r'([a-z]{3,})[- ](\d{1,2})$', date_input.lower().strip())
    if not match:
        await interaction.response.send_message("Invalid date format. Please use 'oct-24' or 'mar-3'.")
        return

    month_str, day_str = match.groups()
    day = int(day_str)
    try:
        month = datetime.datetime.strptime(month_str, '%b').month
    except ValueError:
        await interaction.response.send_message("Invalid month abbreviation.")
        return

    try:
        date_this_year = eastern.localize(datetime.datetime(now.year, month, day))
    except ValueError:
        await interaction.response.send_message("Invalid date.")
        return

    if date_this_year >= now:
        date_to_use = date_this_year
    else:
        date_to_use = eastern.localize(datetime.datetime(now.year + 1, month, day))

    date_str = date_to_use.strftime('%Y-%m-%d')
    if not has_already_posted(date_str):
        await post_meals(date_str)
        mark_as_posted(date_str)
        await interaction.response.send_message(f"Forced menu post for {date_str}")
    else:
        await interaction.response.send_message(f"Menu already posted for {date_str}")

bot.run(BOT_TOKEN)
