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

## Download
	Download: 
	download.sh to download and checks the hash for all PMC bulk files


## Build Database
	Build:
	build.sh to insert all of the publications into a local file sqlite databse

## Retrieve a single paper
	Test:
	test.sh to run a query and retrieve a single paper

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


