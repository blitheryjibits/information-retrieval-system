The search engine takes terms as a ‘bag of words’ i.e., free-text query, then finds documents containing all of the terms in the provided query. The search engine needs to calculate the cosine similarity between the discovered documents and the query using their vector arrays which are made up of their tf-idf values for the query terms. Finally, the search engine must print the document name, cosine similarity, and total number of potential candidates.


<h3>How the program works</h3>
The search engine uses SQLite to query the database provided in the path on line 410. </br>
<strong># #### Path to be edited #### # </strong> </br>
    
    con = sqlite3.connect("c:\sqlite\db\indexer.db")
    
The database is created using the indexer. If a database has not already been created it is possible to do so by running the indexer provided. Note, the indexer takes 3 to 4 minutes to complete on a moderately fast computer due to the number of disk writes required to build the index.

<h3>Initiating the program</h3> 

To run the search engine program, it is necessary to install SQLite on the system (SQLite has a simple and fast tutorial on how to achieve this that takes no more than 10 to 15 minutes to complete). The GUI is not necessary for this task. Alternatively, to view the database in a GUI use the SQLite Viewer application online (this is what I use)

**Indexer**

Choose directory/location to initiate the database and add the path for the database in the indexer program (if running the indexer program) (recommended as functionality between indexers may be different). Note, if the db file doesn’t exist yet, SQLite will automatically make it at the location provided. Line 502
Add the path to the cacm directory. Line 494

Run indexer (may take 3-4 minutes to finish)

Search Engine

Add the database path to the search engine path. Line 410

Run the search engine.

Add the query terms as a string of words with spaces between each word.

**Querying**

To create a query, simply run the program and type in a series of words separated by spaces in the prompt that appears in the terminal. The search engine will separate the query into separate tokens to check against the database. The query terms will also be tokenized in the same manner as the indexer provided, i.e., terms will be removed if they are shorter than 2 letters, or in the list of stop_words on line 356.
Query terms will also be stemmed using the same porter stemmer provided in last weeks assignment so the terms match the termDictionary containing the terms from the cacm corpus.

**Creating Vectors**

The search engine vectorizes the query and document terms separately. That is, the query terms are vectorized by a defined function on line 368.
The document vector array is calculated using the document ids and term ids to query the database and return the precalculated tfidf that was stored in the Posting table created by the indexer from last week. Again, the indexer is provided with code and can be run by simply providing a path to the cacm directory (unzipped) and providing a path for a database that exists or a path to a location that is appropriate for creating the database (can be anywhere on the system. I used the C:\sqlite\db directory that I created after installing sqlite).

**Cosine similarity**

The cosine similarity is calculated in the function defined on line 384. The function uses the dot product of the two vectors and divides that by the product of the two Euclidean normalized vector forms, according to the cosine similarity equation.
Once calculated, the cosine similarity (document relevance) for each document is stored in the resultsList dictionary as {doc_id: similarity) key: value pair.
The cosine similarity is only calculated for the documents containing ALL of the query terms which is identified on line 471.

**Results**

Running the program against the database created from the provided indexer will print:

The Query terms after processing (stemming and filtering stop words)

Program start time	

Name of document, and the cosine similarity (as a list)

Number of total documents containing ALL of the processed query terms

The completion time of the program 
