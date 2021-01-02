import re
import requests
import datetime
import lxml.html as lh
import pandas as pd

def scrapeValues(url, save=False, year=None):
    """Scrapes match data from url
    """
    # Create a handle, page, to handle the contents of the website
    # Get contents and scrape all inside table row <tr></tr> in the main page
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/39.0.2171.95 Safari/537.36'}

    page = requests.get(url, headers=headers)

    doc = lh.fromstring(page.content)
    rows = doc.xpath('//div/table/tbody/tr')

    # pattern matches team name + one word in front with single wild char, such as space
    # then matches a group of two numbers (squad size), then numbers with a . seperator and numbers (mean age)
    # then matches two groups after an euro sign with a million/thousands indicator trailing
    pattern = r"([a-zA-Zøæåö]*?.[[a-zA-Zøæåö]+)(\d\d)(\d+\.*\d+)\€(\d+\.*\d*.)\€(\d+\.*\d*.)"

    teams = []
    for row in rows:
        text = row.text_content()
        # sanitize for regex
        text = text.replace("\n","").replace("\t","")
        # find all pattern matches - if none skip step
        if res := re.search(pattern, text):
            # add partial matches to list of list
            teams.append([
                res.group(1),      # team  
                res.group(2),      # num players
                res.group(3),      # mean age
                res.group(4),      # total value
                res.group(5),      # mean value
            ])

    # Convert to dataframe, add helper data:
    data = pd.DataFrame(teams) 
    data.columns = ["Team", "num_players", "mean_age", "total_value", "mean_value"]

    # convert 1m to 1000000 and 1T to 1000
    def convertToNumber(df):
        df = (df.replace(r'[Tm]+$', '', regex=True).astype(float) * \
                    df.str.extract(r'[\d\.]+([Tm]+)', expand=False)
                    .fillna(1)
                    .replace(['T','m'], [10**3, 10**6]).astype(int))
        return df
        
    data.total_value = convertToNumber(data['total_value'])
    data.mean_value = convertToNumber(data['mean_value'])

    # clean mean age col
    data.mean_age = pd.to_numeric(data.mean_age)

    # clean team names
    data.Team = data.Team.str.replace("ö", "ø")
    
    def removeRepeatedNames(row):
        l = row.split()
        if l[0] == l[1]:
            return l[0]
        else:
            return l[0] + " " + l[1]

    data.Teams = data.Team.apply(removeRepeatedNames)
    
    # add season
    if year is None:
        data['season'] = datetime.datetime.now().year
    else:
        data['season'] = year

    # save data
    data.to_csv("values.csv")

    return data

if __name__ == "__main__":
    print("Starting scrape")
    data = scrapeValues(r"https://www.transfermarkt.com/superligaen/startseite/wettbewerb/DK1/", save=True)
    print("Matches saved.")
    
    # update all seasons
    if False:
        i=0
        while True:
            currentYear = datetime.datetime.now().year
            url = r"https://www.transfermarkt.com/superligaen/startseite/wettbewerb/DK1/plus/?saison_id=" +str(currentYear-i)
            name = str(currentYear-1-i) + "-" + str(currentYear-i)
            data = data.append(scrapeValues(url, False, year=currentYear-i))
            # only data until '91
            if currentYear-1-i < 1992:
                break
            i += 1
        data.to_csv("all.csv")