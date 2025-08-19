import sys
import sqlite3
import tarfile
import zlib
import os
import json
#input is a string, either a pubmed id in numberical form
#or a pubemd central id, beginning PMC
#returns a string as the json of  the publication
#returns an empty list if no id found

#only needed for pyinstaller version
def get_base_path():
    if getattr(sys, 'frozen', False):  # Check if the app is "frozen" (bundled)
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DB_FILE = get_base_path()+'/'+'pmc_ta.db'

def get_pmid_json(pmid, db_file = DB_FILE):
#    pmid = str(pmid)
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

    print("get ",pmid)
    cur = conn.cursor()
    q = 'SELECT abstract,title FROM records WHERE '+select+'=?'
    cur.execute(q, (pmid,))
   
    row = cur.fetchone()
    print(row)
    if row is not None:
        content = row[0]
        title = row[1]        
        output = {"abstract":content,"title":title}
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
 
if len(sys.argv) > 2:
    DB_FILE = sys.argv[2]

output = get_pmid_json(pmid)
output = json.dumps(output)
print(output)
