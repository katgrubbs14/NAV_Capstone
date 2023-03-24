from shiny import App, render, ui, reactive
import pandas as pd
from pathlib import Path
import asyncio
from usp.tree import sitemap_tree_for_homepage
import spacy
from spacy import displacy 
from spacy.lang.en.stop_words import STOP_WORDS
from tqdm import tqdm
import requests
from bs4 import BeautifulSoup
from get_category import *
from get_sub_category import *
from get_location import *
from get_date import *

import numpy as np
import os
import sys



# download text preprocessing information 
nltk.download('punkt')
nltk.download('averaged_perceptron_tagger')
nltk.download('maxent_ne_chunker')
nltk.download('words')

# determine treemap of website urls ###########################
# TODO: what if this fails, can the code be made more robust here?
# try/except logic? probably just exit gracefully
existings_urls_file = Path(__file__).parent / "master_urls_independent.csv" # TODO: file with existing URLs -- does it exist - yes, is it accurate - yes (could be better)?
#kw_file = Path(__file__).parent / "kws.csv"
#subkw_file = Path(__file__).parent / "sub_kws.csv"
existing_df = pd.read_csv(existings_urls_file)
existing_urls = existing_df['url'].to_list()
existing_urls = [*set(existing_urls)] ### removes duplicates from list of existing urls by using the set(), then save them back as a list
tree = sitemap_tree_for_homepage('https://kyivindependent.com/');
urls = [page.url for page in tree.all_pages()]; # pulling the urls from the sitemap
urls = [*set(urls)] ### removes duplicates from urls from sitemap by using the set(), then save them back as a list

# define dataframe for storing gathered urls ##################
# check against existing urls and eliminate them to save time when scraping below
# TODO: what if this fails, can the code be made more robust here?
# try/except logic? fall back to full scrape if this fails?
df = pd.DataFrame(urls) ## urls just pulled from webiste into a new dataframe
df = df.rename(columns={0: 'url'}) # renaming column 0 to "url"
df.to_csv('master_urls_independent.csv', index=False) #  overwriting the master_urls_independent.csv file from this data frame to save scraped urls from sitemap
df['title'] = '' ## addiing column to dataframe 
df['text'] = '' # adding column to data frame
df['incident_type'] = '' # adding column to data frame
df = df[~df["url"].isin(existing_urls)] # remove previously scraped sites from existing url list in this dataframe

# TODO: determine if this code block is needed
#df = df[df["url"].str.contains("/national/")==True]
#df = df[df["url"].str.contains("tag")==False]
#for url in existing_urls:
#    df = df.drop(df[df['url'].str.match(url, na=False)].index)
# print(df)

# for each new url scrape using beautiful soup ################
# store information in Pandas dataframe initialized above
# TODO: what if this fails, can the code be made more robust here?
# try/except logic? probably just fail gracefully 
# TODO: this should be a function and not be repated so many times
current_url = ""
title_text = ""
for index, row in tqdm(df.iterrows(), desc="Loading..."):
    current_url = row[0]
    res = requests.get(current_url)
    html_page = res.content
    soup = BeautifulSoup(html_page, 'html.parser')
    for title in soup.find_all("h1"):
        #for title in soup.find_all('h1', attrs={"class":"newsTitle"}):
        title_text = (title.get_text())
        row[1] = title_text
    for para in soup.find_all('div', attrs={"id":"content", "class":"post_single__content__15w2r"}):
        #for para in soup.find_all('div', attrs={"class":"newsText"}):
        para_text = (para.get_text())
        row[2] += para_text

# use regular expressions to extract key words from scraped text 
# TODO: likely move to an external file so it's easier to add new or remove stale
# this should not be repeated so many times
df = df.replace('\n', '', regex=True)
df = df.replace('shoot down', 'shootdown', regex=True)
df = df.replace('shot down', 'shotdown', regex=True)
df = df.replace('fighter jet', 'fighterjet', regex=True)
df = df.replace('war plane', 'warplane', regex=True)
df = df.replace('kamakazee drone', 'kamakazeedrone', regex=True)
df = df.replace('suicide drone', 'suicidedrone', regex=True)
df = df.replace('naval mine', 'navalmine', regex=True)
df = df.replace('sea mine', 'seamine', regex=True)
df = df.replace('remnants of war', 'remnantsofwar', regex=True)
df = df.replace('unexploded ordance', 'unexplodedordance', regex=True)
df = df.replace('shot at', 'shotat', regex=True)
df = df.replace('cruise missile', 'cruisemissile', regex=True)
df = df.replace('ballistic missile', 'ballisticmissile', regex=True)
df = df.replace('guided missile', 'guidedmissile', regex=True)
df = df.replace('prisoner exchange', 'prisonerexchange', regex=True)
df = df.replace('prisoner swap', 'prisonerswap', regex=True)
df = df.replace('prisoner release', 'prisonerrelease', regex=True)
df = df.replace('special forces', 'specialforces', regex=True)
df = df.replace('strategic withdraw', 'strategicwithdraw', regex=True)
df = df.replace('pull back', 'pullback', regex=True)
df = df.replace('set fire to', 'setfireto', regex=True)
df = df.replace('attempted assassination', 'attemptedassassination', regex=True)
df = df.replace('sentenced to death', 'sentencedtodeath', regex=True)
df = df[df["title"].str.contains("If")==False]
df = df[df["title"].str.contains("What")==False]
df = df[df["title"].str.contains("How")==False]
df = df[df["title"].str.contains("Analysts")==False]
df = df[df["title"].str.contains("visits")==False]

nlp = spacy.load('en_core_web_sm') # TODO: what does this do?

# attempt to determine category ###############################
# this can fail, and when it does you might see "Divide by zero" in the log
# TODO: could there be a better message for failure?
# what should the value be in the dataframe if this fails?
for index, row in tqdm(df.iterrows(), desc="Loading..."):
    title = row[1]
    text = row[2]

    try:   
        category_info = get_category(title, text)
        row[3] = category_info[0]
        #row[4] = np.float64(category_info[1])
    except Exception as e: 
        print(e)
        row[3] = 'none'

df = df[df["incident_type"].str.contains("none")==False] # TODO: what does this do?

# attempt to determine category ###############################
# can this fail? probably ... 
# TODO: try/except?
# what should the value be in the dataframe if this fails?
df['sub_category'] = ' '
for index, row in tqdm(df.iterrows(), desc="Loading..."):
    main_category = row[3]
    title = row[1]
    text = row[2]

    #try:   
    sub_category_info = get_sub_category(main_category, title, text) # call out to get_sub_category module
    row[4] = sub_category_info
        #row[4] = np.float64(category_info[1])
    #except:
        #row[4] = 'none'

# attempt to determine location ###############################
# can this fail? probably ... 
# TODO: try/except?
# what should the value be in the dataframe if this fails?
df['Latitude'] = 1.12
df['Longitude'] = 1.12
df['Date'] = ''
df['City'] = ''
df['Oblast'] = ''
df['Country'] = ''

# call out to get_location module
# can this fail? probably ... 
# TODO: try/except?
# what should the value be in the dataframe if this fails?
applied_df = df.apply(lambda row: pd.Series(get_location(row.url, row.title)), axis=1, result_type='expand')
print(applied_df)

# attempt to determine date ###################################
# can this fail? probably ... 
# TODO: try/except?
# what should the value be in the dataframe if this fails?
df['Date'] = df['url'].apply(get_date)

# create final polished for download ##########################
final_df = pd.DataFrame()
final_df['Latitude'] = applied_df[0]
final_df['Longitude'] = applied_df[1]
final_df['Date'] = df['Date']
final_df['Town'] = applied_df[2]
final_df['Oblast'] = applied_df[3]
final_df['Country'] = applied_df[4]
final_df['Incident_type'] = df['incident_type']
final_df['Incident_sub_type'] = df['sub_category']
final_df['Source_1'] = df['url']

final_df = final_df[final_df['Latitude'] != 11.100000]
final_df = final_df[final_df["Country"].str.contains("UA")==True]
final_df = final_df[final_df["Oblast"].str.contains("NA")==False]

original_list = pd.read_csv("total_independent.csv")
total = pd.concat([original_list, final_df])
total = total.drop_duplicates()
total.to_csv('total_independent.csv', index=False) # save df?

print(final_df) # return df with category, date, and location information

