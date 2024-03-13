import json

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
print("QUOTES BY CATEGORY")
print(quotes_by_category)
