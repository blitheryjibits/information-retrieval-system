import sys
import os
import re
import math
import sqlite3
import time


# use simple dictionary data structures in Python to maintain lists with hash keys
docs = {}
resultslist = {}
queryTermIds = set()


# regular expression or: extract words, extract ID from path, check or hexa value
chars = re.compile(r'\W+')
pattid= re.compile(r'(\d{3})/(\d{3})/(\d{3})')

#
# Docs class: Used to store information about each unit document. In this is the Term object which stores each
# unique instance of termid or a docid.
class Docs:
    terms = {}

#
# Term class: used to store information or each unique termid
class Term:
    docfreq = 0
    termfreq = 0
    idf = 0.0
    tfidf = 0.0

# split on any chars
def splitchars(line) :
    return chars.split(line)

# Implementing the same PorterStemmer class used in the indexer for this project
# to ensure query terms and dictionary terms are stemmed the same way
class PorterStemmer:

    def __init__(self):
        """The main part of the stemming algorithm starts here.
        b is a buffer holding a word to be stemmed. The letters are in b[k0],
        b[k0+1] ... ending at b[k]. In fact k0 = 0 in this demo program. k is
        readjusted downwards as the stemming progresses. Zero termination is
        not in fact used in the algorithm.

        Note that only lower case sequences are stemmed. Forcing to lower case
        should be done before stem(...) is called.
        """

        self.b = ""  # buffer for word to be stemmed
        self.k = 0
        self.k0 = 0
        self.j = 0   # j is a general offset into the string

    def cons(self, i):
        """cons(i) is TRUE <=> b[i] is a consonant."""
        if self.b[i] == 'a' or self.b[i] == 'e' or self.b[i] == 'i' or self.b[i] == 'o' or self.b[i] == 'u':
            return 0
        if self.b[i] == 'y':
            if i == self.k0:
                return 1
            else:
                return (not self.cons(i - 1))
        return 1

    def m(self):
        """m() measures the number of consonant sequences between k0 and j.
        if c is a consonant sequence and v a vowel sequence, and <..>
        indicates arbitrary presence,

           <c><v>       gives 0
           <c>vc<v>     gives 1
           <c>vcvc<v>   gives 2
           <c>vcvcvc<v> gives 3
           ....
        """
        n = 0
        i = self.k0
        while 1:
            if i > self.j:
                return n
            if not self.cons(i):
                break
            i = i + 1
        i = i + 1
        while 1:
            while 1:
                if i > self.j:
                    return n
                if self.cons(i):
                    break
                i = i + 1
            i = i + 1
            n = n + 1
            while 1:
                if i > self.j:
                    return n
                if not self.cons(i):
                    break
                i = i + 1
            i = i + 1

    def vowelinstem(self):
        """vowelinstem() is TRUE <=> k0,...j contains a vowel"""
        for i in range(self.k0, self.j + 1):
            if not self.cons(i):
                return 1
        return 0

    def doublec(self, j):
        """doublec(j) is TRUE <=> j,(j-1) contain a double consonant."""
        if j < (self.k0 + 1):
            return 0
        if (self.b[j] != self.b[j-1]):
            return 0
        return self.cons(j)

    def cvc(self, i):
        """cvc(i) is TRUE <=> i-2,i-1,i has the form consonant - vowel - consonant
        and also if the second c is not w,x or y. this is used when trying to
        restore an e at the end of a short  e.g.

           cav(e), lov(e), hop(e), crim(e), but
           snow, box, tray.
        """
        if i < (self.k0 + 2) or not self.cons(i) or self.cons(i-1) or not self.cons(i-2):
            return 0
        ch = self.b[i]
        if ch == 'w' or ch == 'x' or ch == 'y':
            return 0
        return 1

    def ends(self, s):
        """ends(s) is TRUE <=> k0,...k ends with the string s."""
        length = len(s)
        if s[length - 1] != self.b[self.k]: # tiny speed-up
            return 0
        if length > (self.k - self.k0 + 1):
            return 0
        if self.b[self.k-length+1:self.k+1] != s:
            return 0
        self.j = self.k - length
        return 1

    def setto(self, s):
        """setto(s) sets (j+1),...k to the characters in the string s, readjusting k."""
        length = len(s)
        self.b = self.b[:self.j+1] + s + self.b[self.j+length+1:]
        self.k = self.j + length

    def r(self, s):
        """r(s) is used further down."""
        if self.m() > 0:
            self.setto(s)

    def step1ab(self):
        """step1ab() gets rid of plurals and -ed or -ing. e.g.

           caresses  ->  caress
           ponies    ->  poni
           ties      ->  ti
           caress    ->  caress
           cats      ->  cat

           feed      ->  feed
           agreed    ->  agree
           disabled  ->  disable

           matting   ->  mat
           mating    ->  mate
           meeting   ->  meet
           milling   ->  mill
           messing   ->  mess

           meetings  ->  meet
        """
        if self.b[self.k] == 's':
            if self.ends("sses"):
                self.k = self.k - 2
            elif self.ends("ies"):
                self.setto("i")
            elif self.b[self.k - 1] != 's':
                self.k = self.k - 1
        if self.ends("eed"):
            if self.m() > 0:
                self.k = self.k - 1
        elif (self.ends("ed") or self.ends("ing")) and self.vowelinstem():
            self.k = self.j
            if self.ends("at"):   self.setto("ate")
            elif self.ends("bl"): self.setto("ble")
            elif self.ends("iz"): self.setto("ize")
            elif self.doublec(self.k):
                self.k = self.k - 1
                ch = self.b[self.k]
                if ch == 'l' or ch == 's' or ch == 'z':
                    self.k = self.k + 1
            elif (self.m() == 1 and self.cvc(self.k)):
                self.setto("e")

    def step1c(self):
        """step1c() turns terminal y to i when there is another vowel in the stem."""
        if (self.ends("y") and self.vowelinstem()):
            self.b = self.b[:self.k] + 'i' + self.b[self.k+1:]

    def step2(self):
        """step2() maps double suffices to single ones.
        so -ization ( = -ize plus -ation) maps to -ize etc. note that the
        string before the suffix must give m() > 0.
        """
        if self.b[self.k - 1] == 'a':
            if self.ends("ational"):   self.r("ate")
            elif self.ends("tional"):  self.r("tion")
        elif self.b[self.k - 1] == 'c':
            if self.ends("enci"):      self.r("ence")
            elif self.ends("anci"):    self.r("ance")
        elif self.b[self.k - 1] == 'e':
            if self.ends("izer"):      self.r("ize")
        elif self.b[self.k - 1] == 'l':
            if self.ends("bli"):       self.r("ble") # --DEPARTURE--
            # To match the published algorithm, replace this phrase with
            #   if self.ends("abli"):      self.r("able")
            elif self.ends("alli"):    self.r("al")
            elif self.ends("entli"):   self.r("ent")
            elif self.ends("eli"):     self.r("e")
            elif self.ends("ousli"):   self.r("ous")
        elif self.b[self.k - 1] == 'o':
            if self.ends("ization"):   self.r("ize")
            elif self.ends("ation"):   self.r("ate")
            elif self.ends("ator"):    self.r("ate")
        elif self.b[self.k - 1] == 's':
            if self.ends("alism"):     self.r("al")
            elif self.ends("iveness"): self.r("ive")
            elif self.ends("fulness"): self.r("ful")
            elif self.ends("ousness"): self.r("ous")
        elif self.b[self.k - 1] == 't':
            if self.ends("aliti"):     self.r("al")
            elif self.ends("iviti"):   self.r("ive")
            elif self.ends("biliti"):  self.r("ble")
        elif self.b[self.k - 1] == 'g': # --DEPARTURE--
            if self.ends("logi"):      self.r("log")
        # To match the published algorithm, delete this phrase

    def step3(self):
        """step3() dels with -ic-, -full, -ness etc. similar strategy to step2."""
        if self.b[self.k] == 'e':
            if self.ends("icate"):     self.r("ic")
            elif self.ends("ative"):   self.r("")
            elif self.ends("alize"):   self.r("al")
        elif self.b[self.k] == 'i':
            if self.ends("iciti"):     self.r("ic")
        elif self.b[self.k] == 'l':
            if self.ends("ical"):      self.r("ic")
            elif self.ends("ful"):     self.r("")
        elif self.b[self.k] == 's':
            if self.ends("ness"):      self.r("")

    def step4(self):
        """step4() takes off -ant, -ence etc., in context <c>vcvc<v>."""
        if self.b[self.k - 1] == 'a':
            if self.ends("al"): pass
            else: return
        elif self.b[self.k - 1] == 'c':
            if self.ends("ance"): pass
            elif self.ends("ence"): pass
            else: return
        elif self.b[self.k - 1] == 'e':
            if self.ends("er"): pass
            else: return
        elif self.b[self.k - 1] == 'i':
            if self.ends("ic"): pass
            else: return
        elif self.b[self.k - 1] == 'l':
            if self.ends("able"): pass
            elif self.ends("ible"): pass
            else: return
        elif self.b[self.k - 1] == 'n':
            if self.ends("ant"): pass
            elif self.ends("ement"): pass
            elif self.ends("ment"): pass
            elif self.ends("ent"): pass
            else: return
        elif self.b[self.k - 1] == 'o':
            if self.ends("ion") and (self.b[self.j] == 's' or self.b[self.j] == 't'): pass
            elif self.ends("ou"): pass
            # takes care of -ous
            else: return
        elif self.b[self.k - 1] == 's':
            if self.ends("ism"): pass
            else: return
        elif self.b[self.k - 1] == 't':
            if self.ends("ate"): pass
            elif self.ends("iti"): pass
            else: return
        elif self.b[self.k - 1] == 'u':
            if self.ends("ous"): pass
            else: return
        elif self.b[self.k - 1] == 'v':
            if self.ends("ive"): pass
            else: return
        elif self.b[self.k - 1] == 'z':
            if self.ends("ize"): pass
            else: return
        else:
            return
        if self.m() > 1:
            self.k = self.j

    def step5(self):
        """step5() removes a final -e if m() > 1, and changes -ll to -l if
        m() > 1.
        """
        self.j = self.k
        if self.b[self.k] == 'e':
            a = self.m()
            if a > 1 or (a == 1 and not self.cvc(self.k-1)):
                self.k = self.k - 1
        if self.b[self.k] == 'l' and self.doublec(self.k) and self.m() > 1:
            self.k = self.k -1

    def stem(self, p, i, j):
        """In stem(p,i,j), p is a char pointer, and the string to be stemmed
        is from p[i] to p[j] inclusive. Typically i is zero and j is the
        offset to the last character of a string, (p[j+1] == '\0'). The
        stemmer adjusts the characters p[i] ... p[j] and returns the new
        end-point of the string, k. Stemming never increases word length, so
        i <= k <= j. To turn the stemmer into a module, declare 'stem' as
        extern, and delete the remainder of this file.
        """
        # copy the parameters into statics
        self.b = p
        self.k = j
        self.k0 = i
        if self.k <= self.k0 + 1:
            return self.b # --DEPARTURE--

        # With this line, strings of length 1 or 2 don't go through the
        # stemming process, although no mention is made of this in the
        # published algorithm. Remove the line to match the published
        # algorithm.

        self.step1ab()
        self.step1c()
        self.step2()
        self.step3()
        self.step4()
        self.step5()
        return self.b[self.k0:self.k+1]

# 
# Initailize the Porter stemmer
p = PorterStemmer()

# stop words to remove from query
stop_words = {'am', 'is', 'are', 'was', 'this', 'were', 'be', 'been', 'being', 
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
              
def vectorizeQuery(query) :
    # Initialize an empty dictionary to store term frequencies
    tf_dict = {}
    # Compute term frequencies
    for term in query:
        if term in tf_dict:
            tf_dict[term] += 1
        else:
            tf_dict[term] = 1

    # calculate tf-idf for vectors   
    for term in tf_dict :
        tf_dict[term] = (tf_dict[term]/len(query))

    return tf_dict

def cosineSimilarity(docVector, qVector) :
    # calculate dot product of two vectors
    dotProduct = sum(x * y for x, y in zip(docVector, qVector))
    
    # calculate Euclidean norm that represents the length of the vector in Euclidean space
    docVecNorm = sum(x ** 2 for x in docVector) ** 0.5
    qVecNorm = sum(x ** 2 for x in qVector) ** 0.5
    
    # calculate the Cosine similarity for the vectors
    similarity = dotProduct / (docVecNorm * qVecNorm)
    
    return similarity
    
"""
================================================================================================
>>> main

This section is the 'main' or starting point of the indexer program. The python interpreter will find this 'main' routine and execute it first.
================================================================================================       """
if __name__ == '__main__':

#
# Create a sqlite database to hold the inverted index. The isolation_level statement turns
# on autocommit which means that changes made in the database are committed automatically
# 
# #### Path to be edited #### #
    con = sqlite3.connect("c:\sqlite\db\indexer.db") 
    con.isolation_level = None
    cur = con.cursor()

# Take input from user to query document
    query = input('Enter the search terms, each separated by a space: ')

# Capture the start time of the search so that we can determine the total running
# time required to process the search
    t2 = time.localtime()
    print ('Start Time: %.2d:%.2d:%.2d' % (t2.tm_hour, t2.tm_min, t2.tm_sec))

#
# This routine splits the contents of the query into tokens 
# and removes any noise
# Then stems the words to match the termDictionary
    query = splitchars(query)
    newQuery = []
    for word in query :
        word.replace('\n', '').lower().strip()
        if word in stop_words or len(word) < 3: continue
        else : newQuery.append(p.stem(word, 0, len(word)-1))
    query = newQuery
#
# Get the total number of documents in the collection
    q = "select count(*) from document dictionary"
    cur.execute(q)
    row = cur.fetchone()
    documents = row[0]
#
# If the term exists in the dictionary retrieve all documents for the term and store in a list
    for searchterm in query :
        if row[0] > 0:
            q = "select distinct docid, tfidf, docfreq, termfreq, posting.termid FROM termdictionary, posting where posting.termid = termdictionary.termid and term = '%s' order by docid, posting.termid" % (searchterm)
            cur.execute(q)
            for row in cur:
                i_termid = row[4]
                i_docid = row[0]
                queryTermIds.add(row[4])
                
                if not ( i_docid in docs.keys()):
                    docs[i_docid] = Docs()
                    docs[i_docid].terms = {}

                if not ( i_termid in docs[i_docid].terms.keys()):
                    docs[i_docid].terms[i_termid] = Term()
                    docs[i_docid].terms[i_termid].docfreq = row[2]
                    docs[i_docid].terms[i_termid].termfreq = row[3]
                    docs[i_docid].terms[i_termid].idf = 0.0
                    docs[i_docid].terms[i_termid].tfidf = row[1]

# Determine if all of the query words exist in the corpus
# Iterate over the retrieved documents containing terms from the query and 
# verify they contain all the terms
queryVector = vectorizeQuery(query)

for doc_id, term_id in docs.items():
    # Use term ids to extract the terms from the nested dictionary
    termIds = list(term_id.terms.keys())
    
    # Check that all query terms are in the document
    if all(term in termIds for term in queryTermIds):
    # if True :       
        vectorArray = []
        
        # calculate vector array for document using each term tf-idf value
        for term in termIds :
            vectorArray += [docs[doc_id].terms[term].tfidf]
        
        # Calculate the cosine similarity for each document containing all
        # the terms and add the results to the resultslist dictionary
        similarity = cosineSimilarity(vectorArray, list(queryVector.values()))
        resultslist[doc_id] = similarity

# This line sorts the dictionary in descending order of cosine values
resultslist = dict(sorted(resultslist.items(), key=lambda item: item[1], reverse=True))
i = 0
for doc, val in resultslist.items() :
    i += 1
    # Access databse and retrieve document names that match the resultslist
    # Print document name and cosine similarity
    q = "select DocumentName from documentdictionary where docid = '%d'" % (doc)
    cur.execute(q)
    row = cur.fetchone()
    print ("Document %s has a relevance of %f" % (row[0], val))
    
    # check that only the top 20 are being printed
    if i > 20 : 
        break
con.close()
print (f"Number of documents found containing all of the terms: {len(resultslist)}")

# Print program completion time
t2 = time.localtime()
print ('End Time: %.2d:%.2d:%.2d' % (t2.tm_hour, t2.tm_min, t2.tm_sec))

    