#!/usr/bin/env python
"""Python-Pinboard

Python script for downloading your saved stories and saved comments on Hacker News
and converting them to a JSON format for easy use.

Originally written on Pythonista on iPad
"""

__version__ = "1.1"
__license__ = "BSD"
__copyright__ = "Copyright 2013-2014, Luciano Fiandesio"
__author__ = "Luciano Fiandesio <http://fiandes.io/> & John David Pressman <http://jdpressman.com>"
import os
import pdfkit
import argparse
import time
import re
import sys
import urllib
import urllib.parse as urlparse
import json
from bs4 import BeautifulSoup
import requests
from lxml import html
from types import *
import xml.etree.ElementTree as xml
import tqdm

HACKERNEWS = 'https://news.ycombinator.com'

parser = argparse.ArgumentParser()

parser.add_argument("username", help="The Hacker News username to grab the stories from.")
parser.add_argument("password", help="The password to login with using the username.")
parser.add_argument("-f", "--file", help="Filepath to store the JSON document at.")
parser.add_argument("-n", "--number", default=1, type=int, help="Number of pages to grab, default 1. 0 grabs all pages.")
parser.add_argument("-s", "--stories",  action="store_true", help="Grab stories only.")
parser.add_argument("-c", "--comments", action="store_true", help="Grab comments only.")
parser.add_argument("-pdf", "--pdf", default=1, type=bool, help="Save to PDF")
parser.add_argument("-o", "--output_folder", default="output2/", type=str, help="Output Folder for PDF")
arguments = parser.parse_args()


def save_to_disk(formatted_dict, in_folder):
    options = {
        'quiet': ''
    }
    pbar = tqdm.tqdm(formatted_dict)
    for e in pbar:
        pbar.set_description("Processing %s" % e["title"])

        folder = in_folder + e["title"] + "/"
        if (not os.path.isdir(folder)):
            os.mkdir(folder)
        filename = e["title"] + '.pdf'
        #ARTICLE
        if not os.path.exists(folder+filename):
            try:
                pdfkit.from_url(e["url"], folder+filename, options=options)
                #open(folder+filename, 'wb').write(pdf)
            except:
                print("Could not load url ", e["url"])

        #Comments
        if not os.path.exists(folder + "comments_" + filename):
            url = "https://news.ycombinator.com/item?id=" + str(e["id"])
            try:
                pdfkit.from_url(url, folder + "comments_" + filename, options=options)
                #open(folder + "comments_" + filename, 'wb').write(pdf)
            except:
                print("Could not load url ", url)


        statinfo = os.stat(folder + filename)
        if statinfo.st_size <= 2048:
            #e.append(0)
            print("\n--Error, empty file for ", e["url"])
        #else:
            #e.append(1)


def getSavedStories(session, hnuser, page_range):
    """Return a list of story IDs representing your saved stories. 

    This function does not return the actual metadata associated, just the IDs. 
    This list is traversed and each item inside is grabbed using the Hacker News 
    API by story ID."""
    story_ids = []
    for page_index in page_range:
        saved = session.get(HACKERNEWS + '/upvoted?id=' + 
                            hnuser + "&p=" + str(page_index))
        soup = BeautifulSoup(saved.content, features="lxml")
        for tag in soup.findAll('td',attrs={'class':'subtext'}):
            if tag.a is not type(None):
                a_tags = tag.find_all('a')
                for a_tag in a_tags:
                    if a_tag['href'][:5] == 'item?':
                        story_id = a_tag['href'].split('id=')[1]
                        story_ids.append(story_id)
                        break
    return story_ids

def getSavedComments(session, hnuser, page_range):
    """Return a list of IDs representing your saved comments.

    This function does not return the actual metadata associated, just the IDs.
    This list is traversed and each item inside is grabbed using the Hacker News
    API by ID."""
    comment_ids = []
    for page_index in page_range:
        saved = session.get(HACKERNEWS + '/upvoted?id=' + 
                            hnuser + "&comments=t" + "&p=" + str(page_index))
        soup = BeautifulSoup(saved.content,features="lxml")
        for tag in soup.findAll('td',attrs={'class':'default'}):
            if tag.a is not type(None):
                a_tags = tag.find_all('a')
                for a_tag in a_tags:
                    if a_tag['href'][:5] == 'item?':
                        comment_id = a_tag['href'].split('id=')[1]
                        comment_ids.append(comment_id)
                        break
    return comment_ids


def loginToHackerNews(username, password):
    s = requests.Session() # init a session (use cookies across requests)

    headers = { # we need to specify an header to get the right cookie
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.9; rv:25.0) Gecko/20100101 Firefox/25.0',
        'Accept' : "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }

    # Build the login POST data and make the login request.
    payload = {
        'whence': 'news',
        'acct': username,
        'pw': password
    }
    auth = s.post(HACKERNEWS+'/login', data=payload, headers=headers )
    if 'Bad login' in str(auth.content):
        raise Exception("Hacker News authentication failed!")
    if not username in str(auth.content):
        raise Exception("Hacker News didn't succeed, username not displayed.")

    return s # return the http session

def getHackerNewsItem(item_id):
    """Get an 'item' as specified in the HackerNews v0 API."""
    time.sleep(0.2)
    item_json_link = "https://hacker-news.firebaseio.com/v0/item/" + item_id + ".json"
    try:
        with urllib.request.urlopen(item_json_link) as item_json:
            current_story = json.loads(item_json.read().decode('utf-8'))
            if "kids" in current_story:
                del current_story["kids"]
            return current_story
    except urllib.error.URLError:
        return {"title":"Item " + item_id + " could not be retrieved",
                "id":item_id}

def item2stderr(item_id, item_count, item_total):
    sys.stderr.write("Got item " + item_id + ". ({} of {})\n".format(item_count,
                                                                     item_total))
def get_links(session, url):
    print("Fetching", url)
    response = session.get(url)
    tree = html.fromstring(response.content)
    morelink = tree.xpath('string(//a[@class="morelink"]/@href)')
    return morelink

def main():
    json_items = {"saved_stories":list(), "saved_comments":list()}
    if arguments.stories and arguments.comments:
        # Assume that if somebody uses both flags they mean to grab both
        arguments.stories = False
        arguments.comments = False
    item_count = 0
    session = loginToHackerNews(arguments.username, arguments.password)
    #if n = 0 -> Get the number of pages and parse them
    nb_pages = arguments.number
    if nb_pages == 0:
        nb_pages = 1
        morelink = get_links(session, 'https://news.ycombinator.com/upvoted?id=' + arguments.username)
        while morelink:
            morelink = get_links(session, "https://news.ycombinator.com/" + morelink)
            nb_pages += 1

    print('nb_pages ', nb_pages)

    page_range = range(1, nb_pages + 1)
    if arguments.stories or (not arguments.stories and not arguments.comments):
        print("Getting Stories as JSON")
        story_ids = getSavedStories(session,
                                    arguments.username,
                                    page_range)
        pbar = tqdm.tqdm(story_ids)
        for story_id in pbar:
            should_analyse = True
            #Load the previous json file and check if we already analysed it before
            if os.path.exists(arguments.file) and os.stat(arguments.file).st_size != 0:
                with open(arguments.file) as outfile:
                    data = json.load(outfile)
                    if "saved_stories" in data :
                        for story in data["saved_stories"]:
                            #print(stories)
                            if story_id == str(story["id"]):
                                #print("same")
                                #pbar.set_description("Processing %s" % e[0])
                                should_analyse = False
                                json_items["saved_stories"].append(story)

            if should_analyse:
                json_items["saved_stories"].append(getHackerNewsItem(story_id))
    if arguments.comments or (not arguments.stories and not arguments.comments):
        item_count = 0
        comment_ids = getSavedComments(session,
                                       arguments.username,
                                       page_range)
        for comment_id in comment_ids:
            json_items["saved_comments"].append(getHackerNewsItem(comment_id))
            item_count += 1
            item2stderr(comment_id, item_count, len(comment_ids))
    if arguments.file:
        with open(arguments.file, 'w') as outfile:
            json.dump(json_items, outfile, indent=4)

    if arguments.pdf:
        print("Exporting to PDF")
        output_folder = arguments.output_folder
        if (not os.path.isdir(output_folder)):
            os.mkdir(output_folder)
        save_to_disk(json_items["saved_stories"], output_folder)

if __name__ == "__main__":
    main()
