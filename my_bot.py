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
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))

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

BRUH_CATEGORIES = [
    'Al Forno',
    'Leaf Market',
    'Spoons and Ladles',
    'Hydration',
    'Sweet Treats',
]

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

def get_menu(meal_name, date_str):
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
        if category['name'] in BRUH_CATEGORIES:
            continue
        category_name = CATEGORY_ALIASES.get(category['name'], category['name'])
        menu_lines.append(f"**{category_name}**")
        for item in category.get('items', []):
            menu_lines.append(f"- {item['name']}")
        menu_lines.append('')
    return '\n'.join(menu_lines)

intents = discord.Intents.default()
intents.message_content = True

bot = discord.Client(intents=intents)
tree = discord.app_commands.CommandTree(bot)

@tasks.loop(minutes=1)
async def daily_menu():
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)
    if now.hour == 6 and now.minute == 0:
        date_str = now.strftime('%Y-%m-%d')
        channel = bot.get_channel(CHANNEL_ID)
        if channel is None:
            print(f"Channel with ID {CHANNEL_ID} not found.")
            return
        meals = ['breakfast', 'lunch', 'dinner']
        for meal in meals:
            menu = get_menu(meal, date_str)
            if menu:
                embed = discord.Embed(title=f"{meal.capitalize()} Menu for {date_str}", description=menu, color=0x1D82B6)
                await channel.send(embed=embed)
            else:
                await channel.send(f"No menu available for {meal} on {date_str}")

@daily_menu.before_loop
async def before_daily_menu():
    await bot.wait_until_ready()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    print('------')
    if not daily_menu.is_running():
        daily_menu.start()

    # Sync the application commands with Discord
    await tree.sync()

@tree.command(name="menu", description="Get the dining hall menu")
async def menu(interaction: discord.Interaction, meal: str = None, date_input: str = None):
    eastern = pytz.timezone('US/Eastern')
    now = datetime.datetime.now(eastern)

    await interaction.response.defer()  # Acknowledge the interaction

    if date_input:
        match = re.match(r'([a-z]{3,})[- ](\d{1,2})$', date_input.lower().strip())
        if not match:
            await interaction.followup.send("Invalid date format. Please use format like 'oct-24' or 'mar-3'.")
            return
        month_str, day_str = match.groups()
        day = int(day_str)
        try:
            month = datetime.datetime.strptime(month_str, '%b').month
        except ValueError:
            await interaction.followup.send("Invalid month abbreviation.")
            return
        try:
            date_this_year = eastern.localize(datetime.datetime(now.year, month, day))
        except ValueError:
            await interaction.followup.send("Invalid date.")
            return
        if date_this_year >= now:
            date_to_use = date_this_year
        else:
            date_to_use = eastern.localize(datetime.datetime(now.year + 1, month, day))
    else:
        date_to_use = now

    date_str = date_to_use.strftime('%Y-%m-%d')
    response_messages = []

    if not meal:
        meals = ['breakfast', 'lunch', 'dinner']
        for m in meals:
            menu = get_menu(m, date_str)
            if menu:
                embed = discord.Embed(title=f"{m.capitalize()} Menu for {date_str}", description=menu, color=0x1D82B6)
                response_messages.append(embed)
            else:
                response_messages.append(f"No menu available for {m} on {date_str}")
    else:
        menu = get_menu(meal, date_str)
        if menu:
            embed = discord.Embed(title=f"{meal.capitalize()} Menu for {date_str}", description=menu, color=0x1D82B6)
            response_messages.append(embed)
        else:
            response_messages.append(f"No menu available for {meal} on {date_str}")

    for response in response_messages:
        if isinstance(response, discord.Embed):
            await interaction.followup.send(embed=response)
        else:
            await interaction.followup.send(response)

bot.run(BOT_TOKEN)
