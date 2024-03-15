from flask import Flask, render_template, jsonify, request
import requests
import random
import gspread
import json
import pandas as pd
from dotenv import load_dotenv, find_dotenv
import base64
import os

with open('abbreviation_list.json', 'r') as file:
    abbrevations_to_real = json.load(file)

# get the value of `SERVICE_ACCOUNT_KEY`environment variable
load_dotenv(find_dotenv())
encoded_key = os.getenv("SERVICE_ACCOUNT_KEY")
# decode
credentials = json.loads(base64.b64decode(encoded_key).decode('utf-8'))
selected_database = "DD"

def get_data(worksheet_name):
  gc = gspread.service_account_from_dict(credentials)
  wks = gc.open("CritRat Quote Database")
  print("List of all available worksheets: ", wks.worksheets())
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
          if keyword in abbrevations_to_real:
            keyword = abbrevations_to_real[keyword]
          if keyword in quotes_by_category:
              quotes_by_category[keyword].append(entry)
              pass
          else:
            quotes_by_category[keyword] = [entry]

  df.drop(columns=["KEYWORD_" + str(i) for i in range(1, 13)], inplace=True)

  quote_counter = {}
  for i in quotes_by_category.keys():
    #print("KEY: ", i)
    #print("ITEM: ", quotes_by_category[i])

    quote_counter[i] = len(quotes_by_category[i])

  sorted_categories = sorted(quotes_by_category.keys(), key = lambda x: len(quotes_by_category[x]), reverse=True)
# remove the categories that don't have at least 2 quotes
  sorted_categories = [i for i in sorted_categories if quote_counter[i] > 1]

  return quotes_by_category, quote_counter, sorted_categories, df

quotes_by_category, quote_counter, sorted_categories, df = get_data(selected_database)
data = df[['quote', 'keywords', 'author', 'title']].to_dict(orient='index')

app = Flask(__name__)

@app.route('/')
def index():
    # Pass the data to the template
    return render_template('index.html', sorted_categories=sorted_categories, quote_counter=quote_counter)

@app.route('/keyword/<keyword>')
def word_page(keyword):
    # Here you can do whatever you want with the keyword, 
    # like searching a database, processing it, etc.
    try:
      quotes = quotes_by_category[keyword.replace("_", " ")]
      return render_template('category_template.html', category=keyword, quotes=quotes)
    except:
      print("Category not found: ", keyword)
      return None

@app.route('/random')
def random_item():
    # Randomly select an item from the JSON data
    random_items = quotes_by_category[random.choice(list(quotes_by_category.keys()))]
    random_quote = random.choice(random_items)
    #print(random_quote)
    '''
    random_key_2 = random.choice(list(random_items.keys()))
    random_item = random_items[random_key_2]
    '''
    return render_template('random.html', quote=random_quote)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/search')
def search():
    return render_template('search.html', quotes=data)

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
            print('data', response_data)
        else:
            print('err', response.text)


    return render_template('suggest.html')

def refreshDatabase():
  global quotes_by_category, quote_counter, sorted_categories, data, selected_database
  quotes_by_category, quote_counter, sorted_categories, df = get_data(selected_database)
  data = df[['quote', 'keywords', 'author', 'title']].to_dict(orient='index')

@app.route('/refresh', methods=['GET', 'POST'])
def refresh():
    if request.method == 'POST':
        print("POST request received: ", request.form)
        if 'submit' in request.form:
          print("Data refresh button was pressed")
          try:
            refreshDatabase()
          except:
            print("Error getting data")
            return jsonify({'status': 'error'})
          else:
            print("Data refreshed")
            return jsonify({'status': 'success'})
    elif "dropdown" in request.form:
        print("Dropdown was selected")
        selected_option = request.form.get('dropdown')
        # prevent possible unwanted behavior:
        if (selected_option in {'DD', 'SampleSheet', 'David', 'Vijay', 'Other'}):
          selected_database = selected_option
          print("Attempting to refresh database")
          refreshDatabase()
        else:
          print("Unknown database selected")
        response = make_response("Option saved as cookie!")
        response.set_cookie('selected_database', selected_database)
        return response
    else:
        print("Unknown button was pressed")
    return render_template('refresh.html')

if __name__ == '__main__':
    app.run(debug=True)
