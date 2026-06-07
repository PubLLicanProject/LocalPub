# LocalPuB


## Overview 
This Tool creates a simple Local copy of the Pubmed PMC database
It stores all papers in a local sqlite database, and allows retrieval 
from the Pubmed or PMC id number.  The data remains compressed, so file
sizes are manageable (~110mb as of 9/2024), although downloading and building
still takes multiple hours (but hopefully not multiple days, depending on system)
	
There is also a simple parser to assist in mining text from the publications

To use this, you need to:
	
	1. Download the data - these come from the bulk downloads provided by NCBI
	2. Build a database - insert the file data into the database, without creating files
	3. Test - quickly retrieve and parse json data from the database
	4. Use - as in, do something with it.  

## Installation

First clone the repository to your chosen directory 

	git clone https://github.com/PubLLicanProject/LocalPub.git

Then install the required packages using the command

	pip install -r requirements.txt

## GUI tool

Currently in this version the graphics user interface only supports download functionalities from downloads.py.
In order to run the GUI simply type the command. There may still be bugs in the output printed output for the 
progress bar. This will be fixed in a future update.

	python gui.py
	
There is also a gui for creating queries for the database. However, it is to be noted that some queries
may be very large and can take very long. An example is when querying all the keywords from keywords table of
pmc_kw.

	python queryGui.py

## 1. Download
The tar files can be downloaded using either download.py or download.sh. Download.py can be used
as module to be imported into another file or as CLI. To use download.py as CLI see below:

	python download.py [option] 
	
	option          args
	  -h, --help                     show this help message and exit
      -l 		                     list the downloadable files. Outputs list in a json
      -p 		  [directory]        for use in a pipeline. download all PMC tar files and prints a json in stdout.
      -d 		  [file] [path]      download a file from the link
      -b 		  [directory]        download all PMC tar files on the specified directory.
      -m 		  [md5hash] [file]   Check if file exists. Then, verify file integrity using md5hash.
	
The files may also be downloaded using download.sh. 

	bash download.sh


## 2. Build Database
The database can be built by using the python CLI shown below. This can be used as a module to be run 
on a script or used as CLI or for a pipeline. The options for building the database is shown below.

	python build_db.py

	options:
     -h, --help            show this help message and exit
     -s [db] [filePath]    Process a single tarfile specified in the filePath argument.
     -b [db] [folderPath]  Bulk Process all the tar.gz files in the folderPath specified.
     -p [db] [folderPath]  Bulk process tar.gz in folderPath. For use in a pipeline. Excepts a json stdout from
                           download.py

Builds a database to extract and store each file downloaded file. To insert

	Build:
	build.sh to insert all of the publications into a local file sqlite databse

## Retrieve a single paper
To retrieve a single paper you may use the GUI for querying: queryGui. It will return results based on the SQL
query that you put on the GUI.

	python queryGui.py

You may also run a query to retrieve a single paper by using the bash version of the above.

	test.sh 

## Usage:

	python get_pmid.py <pubmed id>
	python get_pmid.py PMC<pmc id>
	
	examples:
	python get_pmid.py 38205347
	python get_pmid.py PMC10774582
	
	Returns a publication in unicode json format 
	(i.e. it should be indentical to 
	https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/38205347/unicode )
	
	See parse_pubmed_json.py for a useful parser
	
	You may specify the sections to use (the default is all), and it will return 
	a dictionary containing 
	1) text - a complete text of the sections combined, and 
	2) sections - a dictionary of each section separately
	
	See test.py for an example of using the output
	
	Run test.sh to see a working example

## Notes:

Not all PMC papers have pubmid ids
If there are more than one it may be ignored
It's easy to change the build script to use XML or ascii versions, but 
the parser etc. will need to change
(It may be possible to speed up the build with parallelising, but this will not work on a
distributed system)
get_pubmid.py returns the original file inside a json list [] - to match the NCBI api
(If you are using xml, you may want to change this)
For more advanced uses see Using EDirect to create a local copy of PubMed
https://www.nlm.nih.gov/dataguide/edirect/archive.html
This project is deliberately limited in scope.

## Waranty 
No warranty is given or implied, you can see all of the code before deciding if you want
to run it.


