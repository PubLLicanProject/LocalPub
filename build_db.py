import sys
import sqlite3
import tarfile
import zlib
import json
from pathlib import Path

# TODO take a json print input from bash to note what has been downloaded to put in the DB
# TODO from that input in bash read the PATH from where to find the files
# TODO from that input open the tar.gz and process the files and put them inside the DB
# TODO batch these into testable functions that can just be runhel

# TODO automate the task so that it puts it in the DB
# TODO Find things that need automation

stopwords = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"])

batch_data = []
batch_data_keywords = []

# Set batch size (adjust based on available memory and desired performance)
BATCH_SIZE = 1024

# Options
VERBOSE = True


    
# ----------------------------- P I P E L I N E - & - C L I - A R G - H A N D L E R ----------------------------

def options(op):
    """ Handles the options for command line arguments """
    match op:
        
        # bulk process option
        case "-b": return PrepareTarInput()
            
        # Process a single file
        case "-s": return processSysArgs()
        
        # none of the available options were used
        case _:
            print("No such options were found")
            sys.exit()

def processSysArgs():
    """ Process the command line arguments and return a list of paths.
        Do not include Paths that do not exists."""
    return [Path(sys.argv[idx]) for idx in range(len(sys.argv)) if idx > 1 and Path(sys.argv[idx]).resolve().exists()]
    
def PrepareTarInput():
    """ Process the piped json file """
    pyobj = json.loads(sys.stdin.read())
    
    # Get the path passed from bulkdownloads.py
    path = pyobj["Path"]
 
    # Get the download
    tar_file_paths = [Path(path +"/"+ obj).resolve() for obj in pyobj["Downloads"].keys() if obj != "sum"]
    
    # return a list of paths
    return tar_file_paths

# --------------------------------------------- L O G G I N G - F U N C T I O N S -------------------------------------

insdict = {}
errdict = {}
existing = {}

def savelog(code, fileName):
    match code:
        # code for sucessful insertion
        case 100: pass
        
        # code for errors regarding system
        case 200: pass
    
        # code for errors
        case 400: pass # 
        case 401: pass # keyword creation error
        case 403: pass # error inserting
    

def logger():
    """ Log the files in a json format in the chosen directory. """
    obj = {
            "Path": str(PATH_DIR.absolute().resolve),
            "Insertions": insdict,
            "Existing": existing,
            "Errors": errdict
        }
    if PRINTJSON:
        print(json.dumps(obj))
    if MAKELOG:
        with (PATH_DIR / Path("log.json")).open(mode='w') as file:
            json.dump(obj, file)


# ---------------------------------------------- D A T A B A S E - F U N C T I O N S----------------------------------

def checkRecRows():
    """ Check which PMC files are already inserted. """
    pass
    
def checkKwRows():
    """ Check the keywords that are already inserted. """
    pass

def createTableRec(conn, cur):
    """ Create a table for the records """
    
    # Ensure the table exists (you can skip this if you've already created the table)
    cur.execute('''
    CREATE TABLE IF NOT EXISTS records (
        id VARCHAR(32) PRIMARY KEY,
        pmid VARCHAR(32),
        content BLOB
    );
    ''')
    # Makes lookups faster - name index as idx_pmid - create index on the pmid column
    cur.execute('CREATE INDEX IF NOT EXISTS idx_pmid ON records (pmid)')
    conn.commit()

def createTableKw(conn_kw, cur_kw):
    """ Create a table for the keywords. """
    
    cur_kw.execute('''
    CREATE TABLE IF NOT EXISTS keywords (
        keyword VARCHAR(32),
        pmid VARCHAR(32),
        type INTEGER ,
        UNIQUE(keyword, pmid)
    
    ); 
    ''')
    cur_kw.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON keywords (keyword)')
    conn_kw.commit()

def insertRec(conn, cur, batch_data):
    # If batch data is not empty 
    cur.executemany('''
        INSERT OR IGNORE INTO records (id, pmid, content)
        VALUES (?, ?, ?)
    ''', batch_data)
    conn.commit()
    

def insertKW(conn_kw, cur_kw, batch_data_keywords):
    # Commit the final transaction
    cur_kw.executemany('''
        INSERT OR IGNORE INTO keywords (keyword, pmid, type)
        VALUES (?, ?, ?)
    ''', batch_data_keywords)
    conn_kw.commit()
    
# Create table
def createTable(cur, tableName, columns):
    """
    columns = ("col1", "col2", "col3")
    """
    col_def = ", ".join([f"{col} TEXT" for col in columns])
    cur.execute(f"CREATE TABLE IF NOT EXISTS {tableName} ({col_def})")

# Insert values
def insert(cur, tableName, values):
    """
    values = ("A", "B", "C")
    """
    placeholders = ",".join("?" * len(values))
    cur.execute(f"INSERT INTO {tableName} VALUES({placeholders})", values)

    
# ------------------------------------- T A R - F I L E - P R O C E S S I N G-----------------------------------------




def processTar(tar_file_paths, conn, cur, conn_kw, cur_kw):
    """ Process the tar files """
    
    
    
    # remove the xml suffix of the files inside the tar file
    # use tar.extractfile()
    # read the content of the file
    # parse through the json file using the content
    
    for tar_file_path in tar_file_paths:
        if VERBOSE: print(f"opening {tar_file_path}")
    
        # open the tarfile
        with tarfile.open(tar_file_path, 'r:gz') as tar:
            # Iterate through each member in the archive
            for member in tar.getmembers():
                if VERBOSE: print(f"opening {member}")
                # Ensure it's a regular file (skip directories, etc.)
                if member.isfile():
                    
                    # Get the filename (use it as the primary key)
                    filename = member.name.split('/')[-1]  # Only take the filename part (without directory path)
                    filename = filename.removesuffix(".xml")
                    #print(filename)
                    #exit(0)
                    
                    # Extract the file content in memory
                    file_content = tar.extractfile(member).read() # Decoding as UTF-8, adjust if necessary
                    pmid = ""
                    kwd = ""
                    kwdset = set()
                    words = set()
                    try:
                        # assign key-value based on the xml file - into json
                        content_text = file_content.decode('utf-8')
                        content = json.loads(content_text)
                        first = content
                        doc = first['documents']
                        fd = doc[0]
                        p = fd['passages']
                        p0 = p[0]
                        inf = p0['infons']
                        if 'article-id_pmid' in inf:
                            pmid = inf['article-id_pmid']
                        defs=""

        
                        # process the keyword from the infons if it exists
                        if 'kwd' in inf:
                            kwd = inf['kwd']
                            if kwd.count('\n') > 2: # strip the nextlines if there are a lot of nextlines
                                kwdset = set(entry.strip() for entry in kwd.split('\n'))
                            else:
                                kwdset = set(entry.strip() for entry in kwd.split())
                        for x in kwdset:
                            # add them in a list called words (what for?)
                            words.add(x.strip())
                            
                        # need to figure out what def is
                        if 'def' in inf:
                            defs = inf['def']
                        
                        # process the pmid
                        pmid = pmid.strip()
                        for passage in p:
                            inf = passage['infons']  
                            st = inf["section_type"]
                            if st == "ABSTRACT":
                                abstract = passage['text']
                        kwd = defs+" "+ abstract
                    
                    except Exception as e:
                        print("error",e)
                        pass
        
                    # compress content before storing inside the db
                    compressed_content = zlib.compress(file_content)
        
                    # Create a list of the pmid and avoid duplicates if len > 10
                    if len(pmid) > 10:
                        pmids = pmid.split()
                        pmids = list(set(pmids))
                    else:
                        pmids = [pmid]
                    
                    # process the splitted words then add in the original words list
                    words2 = kwd.split()
                    for w in words2:
                        w = w.strip()
                        words.add(w)
                        
                        
                    # process the keywords and append to batch data
                    for pmid in pmids:
                        for word in words:
                            if len(word) > 1 and word.lower() not in stopwords:
                            
                                # Append the entry to batch data
                                if len(word) > 2:
                                    kwtype = 0
                                    if word in kwdset:
                                        kwtype = 1
                                    batch_data_keywords.append((word, pmid, kwtype ))
                                    if word[0].isupper():
                                        word = word[0].lower() + word[1:]
                                        batch_data_keywords.append((word, pmid, kwtype ))
                    
                    # add to batch data for pmid between length 4 and 12
                    for pmid in pmids:
                        if len(pmid) > 4 and len(pmid) < 12:
                            batch_data.append((filename, pmid, compressed_content))
        
                    if len(batch_data) >= BATCH_SIZE:
                        # insert into database if records batch data is geq to preset batch size
                        print(".",end="")
                        insertRec(conn, cur, batch_data)
                        batch_data.clear()  # Clear the batch data
        
                    if len(batch_data_keywords) >= BATCH_SIZE:
                        # insert into database if keywrods batch data is geq to preset batch size
                        print(".",end="")
                        insertKW(conn_kw, cur_kw, batch_data_keywords)
                        batch_data_keywords.clear()  # Clear the batch data

            if batch_data: insertRec(conn, cur, batch_data)
            if batch_data_keywords: insertKW(conn_kw, cur_kw, batch_data_keywords)
        
        return 




# ------------------------------------------------------- M A I N -------------------------------------------------------


def main():
    
    if len(sys.argv) > 1:
        # Check for the option that was printed out 
        tar_file_paths = options(sys.argv[1])
        print(tar_file_paths)
    else:
        print("Please specify the option for the file")
        sys.exit()
    
    
    
    # Create SQLite database connection (or connect to an existing one)
    conn = sqlite3.connect('pmc.db')
    cur = conn.cursor()
    
    # create cursor from the connection
    conn_kw = sqlite3.connect('pmc_kw.db')
    cur_kw = conn_kw.cursor()
    
    # Create the SQLITE tables
    createTableRec(conn, cur)
    createTableKw(conn_kw, cur_kw)

    # Process the tar files 
    processTar(tar_file_paths, conn, cur, conn_kw, cur_kw)
    
    conn.close()
    conn_kw.close()
    print("End")
    return 0

 
main()
