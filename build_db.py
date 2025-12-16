import sys
import sqlite3
import tarfile
import zlib
import json
import argparse
from pathlib import Path


stopwords = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"])
batch_data = []
batch_data_keywords = []

# Set batch size (adjust based on available memory and desired performance)
BATCH_SIZE = 1024

# Options
VERBOSE = True
log = {"Failed": {}}


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


def processTar(tar_file_paths, conn, cur, conn_kw, cur_kw):
    """ Process the tar files """
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

                    except KeyboardInterrupt:
                        print("User Interrupted process")
                        sys.exit(1)
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


def connectDb(path):
    # Create SQLite database connection (or connect to an existing one)
    if (Path(path).resolve()).exists():
        if path.split("/")[-1] == "db":
            try:
                conn = sqlite3.connect(path)
                conn_kw = sqlite3.connect(path)
                cur = conn.cursor()
                cur_kw = conn_kw.cursor()
            except:
                conn = sqlite3.connect(path + '/pmc.db')
                conn_kw = sqlite3.connect(path + '/pmc_kw.db')
                cur = conn.cursor()
                cur_kw = conn_kw.cursor()
        else:
            conn = sqlite3.connect(path + '/pmc.db')
            conn_kw = sqlite3.connect(path + '/pmc_kw.db')
            cur = conn.cursor()
            cur_kw = conn_kw.cursor()
    else:
        Path("./pub").mkdir(exist_ok=True)
        conn = sqlite3.connect('./pub/pmc.db')
        conn_kw = sqlite3.connect('./pub/pmc_kw.db')
        cur = conn.cursor()
        cur_kw = conn_kw.cursor() 

    #Create the SQLITE tables
    createTableRec(conn, cur)
    createTableKw(conn_kw, cur_kw)
    
    return conn, conn_kw, cur, cur_kw

 
def processPaths(path):
    # get the paths of the tarfiles - return a list
    if Path(path).resolve().is_file:
         return [path]

    elif Path(path).resolve().is_dir:
        p =  Path(path).resolve().glob('*.tar.gz')
        files = [x for x in p if x.is_file()]
        if len(files) == 0:
            print("no tar.gz files to put in database")
            sys.exit(0)
        return files
    else:
         raise FileNotFoundError(f"Directory does not exist: {path}")

       
def PrepareTarInput():
    """ Process the piped json file for path and files """
    pyobj = json.loads(sys.stdin.read())
    path = pyobj["Path"]
    tar_file_paths = [Path(path +"/"+ obj).resolve() for obj in pyobj["Downloads"].keys() if obj != "sum"]
    
    return tar_file_paths

   
def jsonProcess(obj):
    """ Receive the json object from the downloads. expect obj -> dict"""
    downloads = obj["Downloads"].keys()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
    prog='python build_db.py',
    description = """ Database Building Tools for https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC.
                      There are two databases created for records and keywords.
                      inside pmc.db is a table called 'records' and inside pmc_kw is a database called 'keywords'. 
                      The records table have columns (attributes): id, pmid, and content. The 'keyword' table has 
                      columns (attributes) keyword, pmid, and type. Information from the tarfile is processed and 
                      inserted into the databases. The content in records is compressed using the DEFLATE algorithm
                      used in the zlib module. Therfore, decompression must be performed to make content readable.
                      Note: [db] is the path to the database ex: C:/Documents/pmc.db; [file/folderPath] is the path 
                      to the tar.gz file or folder.
                  """
    )
    
    # option and constraints
    parser.add_argument('-s', metavar=("[db]", "[filePath]"), type=str, nargs=2, help="Process a single tarfile specified in the filePath argument.")
    parser.add_argument('-b', metavar=("[db]", "[folderPath]"), type=str, nargs=2, help="Bulk Process all the tar.gz files in the folderPath specified.")
    parser.add_argument('-p', metavar=("[db]", "[folderPath]"), type=str, nargs=2, help="Bulk process tar.gz in folderPath. For use in a pipeline. Excepts a json stdout from download.py")
    args = parser.parse_args()

    # print help msg if no arguments passed
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)

    # only get argument != None
    cliArgs = vars(args)
    for key, value in cliArgs.copy().items():
        if cliArgs[key] != False and cliArgs[key] != None: 
            op = key

    # establish connection
    conn, conn_kw, cur, cur_kw = connectDb(cliArgs[op][0])
    
    match op: # cases for arguments
        
        case "s": # process a single tarfile
            tar_file_paths = processPaths(cliArgs[op][1])
            print(f"Processing {tar_file_paths}")
            processTar(tar_file_paths, conn, cur, conn_kw, cur_kw)
            print("done processing tarfile")

        case "b": # download a file with its filename
            print("Beginning Bulk processing of tar files for the database")
            tar_file_paths = processPaths(cliArgs[op][1])
            processTar(tar_file_paths, conn, cur, conn_kw, cur_kw)
            print("done bulk processing tarfile")
            
        case "p": # for use in a pipeline
            tar_file_paths = PrepareTarInput()
            processTar(tar_file_paths, conn, cur, conn_kw, cur_kw)
            print("done")
    
    conn.close()
    conn_kw.close()
    print("End")