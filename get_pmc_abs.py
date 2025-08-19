import sys
import sqlite3
import tarfile
import zlib
import os
import json
import base64

#input is a string, either a pubmed id in numberical form
#or a pubemd central id, beginning PMC
#returns a string as the json of  the publication
#returns an empty list if no id found

#only needed for pyinstaller version
title_only = False


def get_base_path():
    if getattr(sys, 'frozen', False):  # Check if the app is "frozen" (bundled)
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DB_FILE = get_base_path()+'/'+'pmc_ta.db'

def get_pmid_json(pmid, db_file = DB_FILE):
    pmid = str(pmid)
    try:    
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    except:
         print(f"['Error : no database file {db_file}]")
         return[]
         
    output = {}
    select = "pmid"
     
    if pmid.startswith("PMC"):
        select ="id"
        pmid = pmid[3:]
    try:
        pmid = int(pmid)
    except:
        pmid = -1

    cur = conn.cursor()
    q = 'SELECT abstract,title,date FROM records WHERE '+select+'=?'
    if title_only:
        q   = 'SELECT title,date FROM records WHERE '+select+'=?'

    cur.execute(q, (pmid,))
   
    row = cur.fetchone()
    
    if row is not None:
        
        if title_only:
            
            title = row[0]        
            date = row[1]      
                    
            output = {"title":title,"date":date}
        else:
            content = row[0]
            title = row[1]        
            date = row[2]        
            output = {"abstract":content,"title":title,"date":date}

        #if data is compressed
        if isinstance(content, bytes):
            compressed_content = row[0]
            try:
    #content is stored in db as zlib compressed binary content
                decompressed_content = zlib.decompress(compressed_content)
                output["abstract"] = decompressed_content.decode('utf-8')

            except zlib.error as e:
                pass

    conn.close()
    return output


#give an empty answer if no input specified
pmid = "0"
if len(sys.argv) > 1:
    pmid = sys.argv[1]
    if pmid=="-b":
        decoded_bytes = base64.b64decode(sys.argv[2])
        pmid = decoded_bytes.decode("utf-8")  # Convert bytes to string
        pmids = json.loads(pmid)
    if pmid == "-t":
        title_only = True
        pmid = sys.argv[2]


output_data = {}
pmids = json.loads(pmid)

for pmid in pmids:
    output_data[pmid] = get_pmid_json(pmid)

output = json.dumps(output_data)
print(output)
