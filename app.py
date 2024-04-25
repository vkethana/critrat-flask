from flask import Flask, render_template, jsonify, request, make_response
import requests
import pandas as pd
import time
from get_data import get_data, database_list, default_database
import random
import json

user_request_times = {}
database_dict = {}

# TODO add a way to iterate through all the databases without manual entry
for s in database_list:
  database_dict[s] = get_data(s)

app = Flask(__name__)

def categorize_words(words):
    categorized_words = {chr(ord('a') + i): [] for i in range(26)}  # Generate empty categories for each letter

    for word in words:
        first_letter = word[0].lower()
        if first_letter.isalpha():
            categorized_words[first_letter].append(word)
        else:
            second_letter = word[1].lower()
            categorized_words[second_letter].append(word)

    return categorized_words

def get_appropriate_database(category=None):
  try:
    if (category != None):
      return database_dict[category]
    else:
      return database_dict[request.cookies.get('selected_option')]
  except:
    print("Could not get the selected option from the cookie")
    selected_option = None
    print("Defaulting to the primary database.")
    return database_dict[default_database]

@app.route('/')
def index():
    stuff = get_appropriate_database()
    sorted_categories = stuff['sorted_categories']
    quote_counter = stuff['quote_counter']
    # Pass the data to the template
    try:
      selected_database = request.cookies.get('selected_option')
    except:
      selected_database = default_database

    return render_template('index.html', categorized_words=categorize_words(sorted_categories), quote_counter=quote_counter, selected_database=selected_database)

@app.route('/<category>/<keyword>')
def word_page(category, keyword):
    if (keyword == 'inf'):
      keyword = 'infinity'

    stuff = get_appropriate_database(category)
    try:
      quotes_by_category = stuff['quotes_by_category']
      quotes = quotes_by_category[keyword.replace("_", " ")]
      return render_template('category_template.html', category=keyword.replace('_', ' ').title(), quotes=quotes)
    except Exception as e:
      print("Error loading quote: ", e)
      return render_template('404.html')

@app.route('/random')
def random_item():
    stuff = get_appropriate_database()
    quotes_by_category = stuff['quotes_by_category']

    # Randomly select an item from the JSON data
    random_items = quotes_by_category[random.choice(list(quotes_by_category.keys()))]
    random_quote = random.choice(random_items)
    return render_template('random.html', quote=random_quote)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search')
def search():
    quotes = get_appropriate_database()['data']
    return render_template('search.html', quotes=quotes)

@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    if request.method == 'POST':
        # Get the form data from the request
        form_data = request.form
        captcha_response = request.form['g-recaptcha-response']
        form_data = dict(form_data)
        form_data['gCaptchaResponse'] = captcha_response

        url = 'https://script.google.com/macros/s/AKfycbzat_gUO8Vw1jvfgHFsAh_GNVYi4AzDH3061DnsRa68jLqpX20-uVxJOBL16AG0bPw/exec'
        headers = {'Content-Type': 'text/plain;charset=utf-8'}

        response = requests.post(url, headers=headers, data=json.dumps(form_data))

        if response.status_code == 200:
            response_data = response.json()

    return render_template('suggest.html')

def refreshDatabase(targeted_refresh=None):
  if targeted_refresh != None:
    database_dict[targeted_refresh] = get_data(targeted_refresh)
  else:
    for db in database_list:
      database_dict[db] = get_data(db)

def handleDropdown(targeted_refresh=None):
  try:
    refreshDatabase(targeted_refresh)
    return "Database was refreshed successfully."
  except Exception as e:
    return "Error refreshing database: " + str(e)
  else:
    return "Invalid option was selected."

@app.before_request
def limit_refresh_rate():
    if request.path == '/refresh' and request.method == 'POST':
        # Get user's IP address (you may need to use request.remote_addr or another identifier if behind a proxy)
        user_ip = request.remote_addr

        # Get current timestamp
        current_time = time.time()

        # Check if the user has made more than 3 requests in the last minute
        if user_ip in user_request_times:
            request_times = user_request_times[user_ip]
            request_times = [t for t in request_times if current_time - t <= 60]
            if len(request_times) >= 10:
                msg = "ERROR: You have made too many refresh requests. Please wait a bit and try again."
                response = make_response(render_template('refresh.html', selected_option=str(default_database), message=msg))
                return response

        # Update the request times for the user
        if user_ip not in user_request_times:
            user_request_times[user_ip] = []
        user_request_times[user_ip].append(current_time)

@app.route('/refresh', methods=['GET', 'POST'])
def refresh():
  if request.method == 'POST':
      option = request.form.get('option')  # Use request.form.get to handle missing keys

      if option == None:
        print("Invalid option was selected")

      msg = handleDropdown(targeted_refresh=option)
      response = make_response(render_template('refresh.html', selected_option=option, message=msg))
      response.set_cookie('selected_option', option)
      return response
  else:
      selected_option = request.cookies.get('selected_option')
      return render_template('refresh.html', selected_option=selected_option)

if __name__ == '__main__':
    app.run(debug=True)
