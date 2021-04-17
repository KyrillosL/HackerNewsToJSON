# Hacker News to PDF #

Save 'saved stories' from a Hacker News account to PDF and JSON

The script parses the saved stories page on HN (http://news.ycombinator.com) and, for each link on each page of the saved stories history it outputs an entry to a JSON document with information taken from the Hacker News API. (https://github.com/HackerNews/API)

The script is meant to be launched from the command line.

Originally developed on iPad by Luciano Fiandesio with the awesome Pythonista (http://omz-software.com/pythonista/), modified for JSON output by John David Pressman and pdf export added by Kyrillos_L

## How to use ##

`python hn2pdf.py [hn user] [hn password] -f [JSON filename] -pdf [0/1] -o [Output Folder]`

``OPTIONAL : -n [Number of pages to grab], nothing = all pages` 

