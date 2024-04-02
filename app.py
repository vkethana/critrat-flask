from flask import Flask, render_template, jsonify, request, make_response
import requests
import random
import gspread
import json
import pandas as pd
import base64
import os
import time

encoded_key = os.getenv("SERVICE_ACCOUNT_KEY")
credentials = json.loads(base64.b64decode(encoded_key).decode('utf-8'))
selected_database = "DD"
database_dict = {}
max_character_count = 500
amount_per_category = 3
user_request_times = {}

with open('data/abbreviation_list.json', 'r') as file:
    abbreviations_to_real = json.load(file)

def get_data(worksheet_name):
  gc = gspread.service_account_from_dict(credentials)
  wks = gc.open("CritRat Quote Database")
  #print("List of all available worksheets: ", wks.worksheets())
  print("Loading the database: ", worksheet_name)
  wks = wks.worksheet(worksheet_name)
  df = pd.DataFrame(wks.get_all_records())
  df['keywords'] = ''

  rows_to_check = ["KEYWORD_" + str(i) for i in range(1,13)]
  all_keywords = set()
  quotes_by_category = {}

  for index, row in df.iterrows():
      found_keywords = set()
      for r in rows_to_check:
          if (row[r] != ''):
              found_keywords.add(row[r])
              all_keywords.add(row[r])
      df.at[index, 'keywords'] = found_keywords
      if found_keywords:
        for keyword in found_keywords:
          entry = {"Quote": row['quote'], "Source": row['author'] + ", " + row['title']}
          if keyword in abbreviations_to_real:
            keyword = abbreviations_to_real[keyword]
          if keyword in quotes_by_category:
              if len(row['quote']) < max_character_count:
                quotes_by_category[keyword].append(entry)
          else:
            quotes_by_category[keyword] = [entry]

  df.drop(columns=["KEYWORD_" + str(i) for i in range(1, 13)], inplace=True)

  quote_counter = {}
  for i in quotes_by_category.keys():
    #print("KEY: ", i)
    #print("ITEM: ", quotes_by_category[i])

    quote_counter[i] = len(quotes_by_category[i])

  sorted_categories = sorted(quotes_by_category.keys(), key = lambda x: len(quotes_by_category[x]), reverse=True)

  # remove the categories that don't have at least "N" quotes for arbitrary n
  sorted_categories = [i for i in sorted_categories if (quote_counter[i] >= amount_per_category) and (i != '') and (i != float('inf'))]

  retval = {
    "quotes_by_category": quotes_by_category,
    "quote_counter": quote_counter,
    "sorted_categories": sorted_categories,
    "df": df,
    "data": df[['quote', 'keywords', 'author', 'title']].to_dict(orient='index')
  }
  return retval

# TODO add a way to iterate through all the databases without manual entry
for selected_database in ["DD",  "David", "Vijay", "Other"]:
  database_dict[selected_database] = get_data(selected_database)

app = Flask(__name__)

def get_appropriate_database():
  try:
    selected_option = request.cookies.get('selected_option')
    return database_dict[selected_option]
  except:
    print("Could not get the selected option from the cookie")
    selected_option = None
    print("Loading database for DD")
    return database_dict['DD']

@app.route('/')
def index():
    stuff = get_appropriate_database()
    sorted_categories = stuff['sorted_categories']
    #print("sorted_categories: ", sorted_categories)
    quote_counter = stuff['quote_counter']
    # Pass the data to the template
    return render_template('index.html', sorted_categories=sorted_categories, quote_counter=quote_counter)

@app.route('/keyword/<keyword>')
def word_page(keyword):
    if (keyword == 'inf'):
      keyword = 'infinity'

    stuff = get_appropriate_database()
    try:
      quotes_by_category = stuff['quotes_by_category']
      quotes = quotes_by_category[keyword.replace("_", " ")]

      return render_template('category_template.html', category=keyword.replace('_', ' ').title(), quotes=quotes)
    except:
      return render_template('404.html')

@app.route('/random')
def random_item():
    stuff = get_appropriate_database()
    quotes_by_category = stuff['quotes_by_category']

    # Randomly select an item from the JSON data
    random_items = quotes_by_category[random.choice(list(quotes_by_category.keys()))]
    random_quote = random.choice(random_items)
    #print(random_quote)
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
        #print(form_data)
        form_data = dict(form_data)
        form_data['gCaptchaResponse'] = captcha_response
        #print(form_data)

        url = 'https://script.google.com/macros/s/AKfycbzat_gUO8Vw1jvfgHFsAh_GNVYi4AzDH3061DnsRa68jLqpX20-uVxJOBL16AG0bPw/exec'
        headers = {'Content-Type': 'text/plain;charset=utf-8'}

        response = requests.post(url, headers=headers, data=json.dumps(form_data))

        if response.status_code == 200:
            response_data = response.json()
            #print('data', response_data)
        else:
            #print('err', response.text)
            pass

    return render_template('suggest.html')

def refreshDatabase(targeted_refresh=None):
  if targeted_refresh != None:
    #print("Only refreshing the targeted database: ", targeted_refresh)
    database_dict[targeted_refresh] = get_data(targeted_refresh)
  else:
    for db in ["DD", "David", "Vijay", "Other"]:
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
            if len(request_times) >= 3:
                msg = "ERROR: You have made too many refresh requests. Please wait a bit and try again."
                response = make_response(render_template('refresh.html', selected_option='DD', message=msg))
                return response

        # Update the request times for the user
        if user_ip not in user_request_times:
            user_request_times[user_ip] = []
        user_request_times[user_ip].append(current_time)

@app.route('/refresh', methods=['GET', 'POST'])
def refresh():
  if request.method == 'POST':
      #print("POST request received: ", request)
      option = request.form.get('option')  # Use request.form.get to handle missing keys

      if option == None:
        print("Invalid option was selected")

      msg = handleDropdown(targeted_refresh=option)
      response = make_response(render_template('refresh.html', selected_option=option, message=msg))
      response.set_cookie('selected_option', option)
      return response
  else:
      selected_option = request.cookies.get('selected_option')
      #print("selected option is ", selected_option)
      return render_template('refresh.html', selected_option=selected_option)

if __name__ == '__main__':
    app.run(debug=True)
    #pass
