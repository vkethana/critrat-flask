import gspread
import json
import pandas as pd
import base64
import os

encoded_key = os.getenv("SERVICE_ACCOUNT_KEY")
credentials = json.loads(base64.b64decode(encoded_key).decode('utf-8'))

database_list = ["primary",  "david", "misc1", "misc2"]
default_database = database_list[0]
assert (database_list[0] == "primary"), "The first database should be the primary database"
selected_database = default_database
max_character_count = 500
amount_per_category = 2

with open('data/abbreviation_list.json', 'r') as file:
    abbreviations_to_real = json.load(file)

def get_data(worksheet_name):
  gc = gspread.service_account_from_dict(credentials)
  wks = gc.open("CritRat Quote Database")
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
          # check if the quote has a line break and if so print it out
          if "\n" in row['quote']:
            # split the quote into a list of lines
            lines = [i for i in row['quote'].split("\n") if i != '']
            entry = {
              "Quote": row['quote'],
              "Author": row['author'],
              "Title": row['title'],
              "isMultiLine": True,
              "lines": lines
            }
          else:
            entry = {
              "Quote": row['quote'],
              "Author": row['author'],
              "Title": row['title'],
              "isMultiLine": False
            }

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

