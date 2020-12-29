import re
import requests
import lxml.html as lh
import pandas as pd

url = r"https://superstats.dk/program"

# Create a handle, page, to handle the contents of the website
# Get contents and scrape all inside table row <tr></tr> in the main page
page = requests.get(url)
doc = lh.fromstring(page.content)
rows = doc.xpath('//tr')

# format follows: weekday _ dd/mm tt:mm klub1-blub2 score-score
pattern = r"([A-Z][a-zø][a-z]).+(\d\d/\d\d).+\d+([a-zA-Z]+-[a-zA-Z]+)(\d-\d)"

matches = []
for row in rows:
    text = row.text_content()
    # sanitize for regex
    text = text.replace("\n","").replace("\t","")
    # find all pattern matches - if none skip step
    if res := re.search(pattern, text):
        # add partial matches to list of list
        match =[
            res.group(1),                   # weekday  
            res.group(2)                    # date
        ]
        match += res.group(3).split("-")    # teams
        match += res.group(4).split("-")    # score
        matches.append(match)

# Convert to dataframe, add helper data:
data = pd.DataFrame(matches) 
data.columns = ["Dag", "dato", "hjemme", "modstander", "score", "score_imod"]

# get reverse matches and reorder
reverseMatches = data.copy()
reverseMatches.columns = ["Dag", "dato", "modstander", "hjemme", "score_imod", "score"]
reverseMatches = reverseMatches[["Dag", "dato", "hjemme", "modstander", "score", "score_imod"]]

# add home or away flag
reverseMatches["homefield"] = 0
data["homefield"] = 1

# combine
data = data.append(reverseMatches)


# add points
def points(row):
    if row.score>row.score_imod:
        return 3
    elif row.score == row.score_imod:
        return 1
    else:
        return 0

data["point"] = data.apply(points, axis=1)

# save
data.to_csv("currentSeason.csv")
