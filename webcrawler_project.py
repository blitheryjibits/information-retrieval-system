import sys, os, re
from urllib.request import Request, urlopen
from urllib.parse import urlparse, urljoin
import sqlite3
import math
import time
from bs4 import BeautifulSoup
import hashlib
from nltk.stem import PorterStemmer


tokens = 0
documents = 0
terms = 0
removedStopWords = 0
chunk = 0

# Create a term object for each unique instance of a term
class Term():
    termid = 0 
    termfreq = 0
    docs = 0 
    docids = {}

database = {}

chars = re.compile(r'\W+')
pattid= re.compile(r'(\d{3})/(\d{3})/(\d{3})')

# Instantiate the nltk Porter Stemmer
p = PorterStemmer()

# List of stop words to be removed during text preprocessing
stop_words = {'am', 'is', 'the', 'are', 'was', 'were', 'be', 'been', 'being', 
              'do', 'does', 'did', 'doing', 'a', 'an', 'but', 'if', 'or', 
              'because', 'as', 'until', 'while', 'of', 'at', 'by', 'for', 
              'with', 'about', 'against', 'between', 'into', 'through', 
              'during', 'before', 'after', 'above', 'below', 'to', 'from', 
              'up', 'down', 'in', 'out', 'on', 'off', 'over', 'under', 
              'again', 'further', 'then', 'once', 'here', 'there', 'when', 
              'where', 'why', 'how', 'all', 'any', 'both', 'each', 'few', 
              'more', 'most', 'other', 'some', 'such', 'no', 'nor', 'not', 
              'only', 'own', 'same', 'so', 'than', 'too', 'very', 'can', 
              'will', 'just', 'don', 'should', 'now'}

# split on any chars.
# filter(none) removes white spaces, space characters (\n,\t, etc), 
# and punctuation
def splitchars(line) :
    return list(filter(None, chars.split(line)))

# process the tokens of the source code 
def parsetoken(line):
    global documents, tokens, terms, removedStopWords, chunk
    line = re.sub(r'\d+', ' ', line)
    l = splitchars(line)

    # for each token in the line 
    for elmt in l:
        # This statement converts all letters to lower case
        lowerElmt = elmt.lower().strip()
        
        # Identify and count stopped words
        # continue skips the rest of the loop, effectively removing stop words
        # from being processed 
        if lowerElmt in stop_words: 
            removedStopWords += 1
            tokens += 1
            continue
            
        if len(lowerElmt) > 2 :
            
        # Stem word before adding to database
            lowerElmt = p.stem(lowerElmt)
            tokens += 1
            chunk += 1
            
            # Add unique terms to database
            if not (lowerElmt in database.keys()): 
                terms+=1
                database[lowerElmt] = Term() 
                database[lowerElmt].termid = create_unique_id(lowerElmt)
                database[lowerElmt].docids = dict() 
                database[lowerElmt].docs = 0
                    
                # Add term to postings list if term is not already there
            if not (documents in database[lowerElmt].docids.keys()): 
                database[lowerElmt].docs += 1
                database[lowerElmt].docids[documents] = 0
            
            # Increment term frequency
            database[lowerElmt].termfreq += 1
            # Increment {docids:value+=1} for term which represents the term frequency 
            # inside the current document
            database[lowerElmt].docids[documents] += 1

    
    return l

def create_unique_id(word):
    return hashlib.sha256(word.encode()).hexdigest()

#
# Create the inverted index tables.
#
# Insert a row into the TermDictionary for each unique term along with a termid which is
# a integer assigned to each term through a hashlib function that creates a unique
# value for each word
#
# Insert a row into the posting table for each unique combination of Docid and termid
#
def writeindex(db):
        term_data = []
        posting_data = []
        for k in db.keys():
                term_data.append((k, db[k].termid))
                docfreq = db[k].docs
                ratio = float(documents) / float(docfreq)
                idf = math.log10(ratio)

                for i in db[k].docids.keys():
                        termfreq = db[k].docids[i]
                        tfidf = float(termfreq) * float(idf)
                        if tfidf > 0:
                            posting_data.append((db[k].termid, i, tfidf, docfreq, termfreq))
        
        # Insert data into the database using batch insertion
        t2 = time.localtime()
        print ('Inserting terms into term table: %.2d:%.2d:%.2d' % (t2.tm_hour, t2.tm_min, t2.tm_sec))
        cur.executemany('insert into TermDictionary values (?,?)', term_data)
        
        t2 = time.localtime()
        print ('Inserting postings into Posting table: %.2d:%.2d:%.2d' % (t2.tm_hour, t2.tm_min, t2.tm_sec))
        cur.executemany('insert into Posting values (?, ?, ?, ?, ?)', posting_data)

        
if __name__ == '__main__':

# Get the starting URL to crawl
    line = input("Enter URL to crawl (must be in the form http://www.domain.com): ")

# Create a sqlite database to hold the inverted index.
    con = sqlite3.connect("c:\sqlite\db\webcrawler.db")  # path to be edited
    con.isolation_level = None
    cur = con.cursor()

#
# In the following section three tables and their associated indexes will be created.
# Before we create the table or index we will attempt to drop any existing tables in
# case they exist
#
# Document Dictionary Table
    cur.execute("drop table if exists DocumentDictionary")
    cur.execute("drop index if exists idxDocumentDictionary")
    cur.execute("create table if not exists DocumentDictionary (DocumentName text, DocId int)")
    cur.execute("create index if not exists idxDocumentDictionary on DocumentDictionary (DocId)")

# Term Dictionary Table
    cur.execute("drop table if exists TermDictionary")
    cur.execute("drop index if exists idxTermDictionary")
    cur.execute("create table if not exists TermDictionary (Term text, TermId int primary key)")
    cur.execute("create index if not exists idxTermDictionary on TermDictionary (TermId)")

# Postings Table
    cur.execute("drop table if exists Posting")
    cur.execute("drop index if exists idxPosting1")
    cur.execute("drop index if exists idxPosting2")
    cur.execute("create table if not exists Posting (TermId int, DocId int, tfidf real, docfreq int, termfreq int)")
    cur.execute("create index if not exists idxPosting1 on Posting (TermId)")
    cur.execute("create index if not exists idxPosting2 on Posting (Docid)")

#
# Capture the start time of the routine so that we can determine the total running
# time required to process the corpus
    t2 = time.localtime()
    print ('Start Time: %.2d:%.2d' % (t2.tm_hour, t2.tm_min))
    

# Initialize variables
    crawled = ([])	    # contains the list of pages that have already been crawled
    tocrawl = [line]	# contains the queue of url's that will be crawled
    links_queue = 0	    # counts the number of links in the queue to limit the depth of the crawl
    crawlcomplete = True    # condition that will exit the while loop when the craw is finished

#
# Crawl the starting web page and links in the web page up to the limit.
    while crawlcomplete:

# Pop the top url off of the queue and process it.
        try:
                crawling = tocrawl.pop()
        except:
                crawlcomplete = False
                continue

    # Parse URL and check extension
        l = len(crawling)
        url = urlparse(crawling)
        ext = os.path.splitext(url.path)[1]
        if ext in ['.pdf', '.png', '.jpg', '.gif', '.asp', '.css']:
            crawled.append(crawling)
            continue

# Print the current length of the queue of URL's to crawl and the URL to crawl
        # print (len(tocrawl),crawling)

# Open the URL.
        headers = {'User-Agent': 'Mozilla/5.0'}
        req = Request(url.geturl(), headers=headers)
        try:
            response = urlopen(req)
            html = response.read()
        except Exception as e:
            print(f"an error occured: {e}")
            continue

# Use BeautifulSoup modules to format web page as text that can
# be parsed and indexed
        soup = BeautifulSoup(html, features="html.parser")
        for script in soup(["script", "style"]):
            script.extract()
        text = soup.get_text()
        
# pass the text extracted from the web page to the parsetoken routine for indexing
# Insert document name and id into the database
        if len(text) > 0:
            parsetoken(text)
            documents += 1
            cur.execute("insert into DocumentDictionary values (?,?)", (url.geturl(), documents))
            # if chunk > 5000:
            #     writeindex(database)
            #     database = {}
            #     chunk = 0
#
# Find all of the weblinks on the page and put them in the stack to crawl through
#
        if links_queue <= 50:
            links = re.findall('''href=["'](.*?\.html)["']''', html.decode('utf-8', 'ignore'), re.I) #(.[^"']+)["']''', html.decode('utf-8', 'ignore'), re.I)
            
            for link in links:
                full_url = urljoin(url.geturl(), link)
                if full_url not in crawled and full_url not in tocrawl:
                    links_queue += 1
                    tocrawl.append(full_url)
                    if len(tocrawl) >= links_queue:
                        break
                    
                crawled.append(full_url)  

# 
# Write index to SQLite database
    writeindex(database)

#
# Display the time that the indexing process
# and writing to databse is complete,
# and print statistics
    t2 = time.localtime()
    print ('Writing to disk complete: %.2d:%.2d:%.2d' % (t2.tm_hour, t2.tm_min, t2.tm_sec))

    print ("Documents processed: %i" % documents)
    print ("Terms found: %i" % terms)
    print ("Tokens processed %i" % tokens)
    print ("Stop Words removed: %i" % removedStopWords)

    