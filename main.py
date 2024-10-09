#!/usr/bin/env python3

import argparse
import datetime
import requests
import sys

CATEGORY_ALIASES = {
    # main categories
    'The Kitchen': 'Main Course Meat Station',
    'Grill House': 'Fried Food and Burgers Station',
    'Global Eats': 'Pasta Station',
    'The Sprout': 'Vegetarian Station',
    'Create': 'DIY but not DIY station',
    'My Pantry': 'DIY Station',
    # bruh categories
    'Al Forno': 'Pizza',
    'Leaf Market': 'Salad Bar',
    'Spoons and Ladles': 'Soups',
    'Hydration': 'Drinks',
    'Sweet Treats': 'Desserts and Fresh Fruit',
}

BRUH_CATEGORIES = [
    'Al Forno',  # pizza
    'Leaf Market',  # salad bar
    'Spoons and Ladles',  # soups
    'Hydration',  # drinks
    'Sweet Treats',  # desserts and fresh fruit
]

def parse_arguments():
    parser = argparse.ArgumentParser(description='Get menu for specified meal and date')
    parser.add_argument('meal', choices=['breakfast', 'lunch', 'dinner'], help='Meal to get menu for')
    parser.add_argument('--date', help='Date in format YYYY-MM-DD')
    return parser.parse_args()

def get_date(args):
    if args.date:
        date_str = args.date
        try:
            datetime.datetime.strptime(date_str, '%Y-%m-%d')
        except ValueError:
            print("Incorrect date format, should be YYYY-MM-DD")
            sys.exit(1)
    else:
        date_str = datetime.date.today().strftime('%Y-%m-%d')
    return date_str

def get_initial_data(date_str):
    url = 'https://api.dineoncampus.ca/v1/location/63f8f1a992d6b40415c69179/periods'
    params = {'platform': '0', 'date': date_str}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
    except ValueError:
        print("Error parsing JSON response")
        sys.exit(1)

def get_meal_data(period_id, date_str):
    url = f'https://api.dineoncampus.ca/v1/location/63f8f1a992d6b40415c69179/periods/{period_id}'
    params = {'platform': '0', 'date': date_str}
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching data: {e}")
        sys.exit(1)
    except ValueError:
        print("Error parsing JSON response")
        sys.exit(1)

def main():
    args = parse_arguments()
    date_str = get_date(args)
    meal_name = args.meal.lower()

    data = get_initial_data(date_str)
    periods = data.get('periods', [])

    period_id = None
    for period in periods:
        if period['name'].lower() == meal_name:
            period_id = period['id']
            break

    if not period_id:
        print(f"No data found for {meal_name} on {date_str}")
        sys.exit(1)

    meal_data = get_meal_data(period_id, date_str)
    categories = meal_data.get('menu', {}).get('periods', {}).get('categories', [])

    if not categories:
        print(f"No menu data available for {meal_name} on {date_str}")
        sys.exit(1)

    for category in categories:
        if category['name'] in BRUH_CATEGORIES:
            continue
        category_name = CATEGORY_ALIASES.get(category['name'], category['name'])
        print(category_name)
        for item in category.get('items', []):
            print(f"\t{item['name']}")

if __name__ == '__main__':
    main()
