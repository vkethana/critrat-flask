from flask import Flask, render_template, jsonify, request
import requests
import random
import json

app = Flask(__name__)

# Read JSON file
with open('abbreviation_list.json', 'r') as file:
    abbrevations_to_real = json.load(file)

def open_data(file_paths):
  # Read JSON file
  data = {}
  for file_path in file_paths:
    print("Reading file path", file_path)
    with open(file_path, 'r') as file:
        data = data | json.load(file)
  print("File read successfully.")
  return data

def get_data(data):

  categories = {}
  for i in data.keys():
      quote = data[i]
      quote_category_list = quote['keywords']

      ***REMOVED***
      text_to_check = quote['quote'].lower()
      is_controversial = any(elem in text_to_check for elem in hidden_keywords) or any(elem in text_to_check.split() for elem in hidden_keywords)

      good_length = len(quote['quote']) < 900

      if ((quote_category_list != []) and (is_controversial == False) and good_length):
        c = quote_category_list[0]
        if (c != 'pattern') and (c != 'the pattern'):
          if c not in categories:
              categories[c] = []
          categories[c].append({'Quote': quote['quote'], 'Source': quote['author']+ ", " + quote['title']})

      else:
        #print("Will NOT show this quote in the site: ", quote['text'], "because it has no keywords / contains controversial material.")
        pass

  new_dict = {}
  for c in categories:
      if c in abbrevations_to_real:
          new_dict[abbrevations_to_real[c]] = categories[c]
      else:
          new_dict[c] = categories[c]
  return new_dict

data = open_data(['naval_brett.json', 'dd.json'])
quotes_by_category = get_data(data)
#print(quotes_by_category)

quote_counter = {}
for i in quotes_by_category.keys():
  #print("KEY: ", i)
  #print("ITEM: ", quotes_by_category[i])

  quote_counter[i] = len(quotes_by_category[i])

sorted_categories = sorted(quotes_by_category.keys(), key = lambda x: len(quotes_by_category[x]), reverse=True)
# remove the categories that don't have at least 2 quotes
sorted_categories = [i for i in sorted_categories if quote_counter[i] > 1]

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
    random_key = random.choice(list(data.keys()))
    random_item = data[random_key]
    #print(random_item)
    return render_template('random.html', quote=random_item)

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
        print(form_data)
        form_data = dict(form_data)
        form_data['gCaptchaResponse'] = captcha_response
        print(form_data)

        url = 'https://script.google.com/macros/s/AKfycbzat_gUO8Vw1jvfgHFsAh_GNVYi4AzDH3061DnsRa68jLqpX20-uVxJOBL16AG0bPw/exec'
        headers = {'Content-Type': 'text/plain;charset=utf-8'}

        response = requests.post(url, headers=headers, data=json.dumps(form_data))

        if response.status_code == 200:
            response_data = response.json()
            print('data', response_data)
        else:
            print('err', response.text)


    return render_template('suggest.html')

if __name__ == '__main__':
    app.run(debug=True)
