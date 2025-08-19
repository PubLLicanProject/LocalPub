import sys
import sqlite3
import tarfile
import zlib
import json

stopwords = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now"])


# Create SQLite database connection (or connect to an existing one)
conn = sqlite3.connect('pmc.db')
cur = conn.cursor()
conn_kw = sqlite3.connect('pmc_kw.db')
cur_kw = conn_kw.cursor()
# Ensure the table exists (you can skip this if you've already created the table)
cur.execute('''
CREATE TABLE IF NOT EXISTS records (
    id VARCHAR(32) PRIMARY KEY,
    pmid VARCHAR(32),
    content BLOB
);

''')

cur_kw.execute('''
CREATE TABLE IF NOT EXISTS keywords (
    keyword VARCHAR(32),
    pmid VARCHAR(32),
    type INTEGER ,
    UNIQUE(keyword, pmid)
  
);

''')


cur.execute('CREATE INDEX IF NOT EXISTS idx_pmid ON records (pmid)')
 
cur_kw.execute('CREATE INDEX IF NOT EXISTS idx_keywords ON keywords (keyword)')
 
 
conn.commit()
conn_kw.commit()

batch_data = []
batch_data_keywords = []

# Set batch size (adjust based on available memory and desired performance)
BATCH_SIZE = 1024

# Path to your .tar.gz file
tar_file_path = 'PMC000XXXXX_json_unicode.tar.gz'
if len(sys.argv) > 1:
    tar_file_path = sys.argv[1]

print("open",tar_file_path)
# Open the .tar.gz file
with tarfile.open(tar_file_path, 'r:gz') as tar:
    # Iterate through each member in the archive
    for member in tar.getmembers():
        # Ensure it's a regular file (skip directories, etc.)
        if member.isfile():
            # Get the filename (use it as the primary key)
            filename = member.name.split('/')[-1]  # Only take the filename part (without directory path)
            filename = filename.removesuffix(".xml")
#            print(filename)
#            exit(0)
            
            # Extract the file content in memory
            file_content = tar.extractfile(member).read() # Decoding as UTF-8, adjust if necessary

            pmid = ""
            kwd=""
            kwdset = set()
            words = set()
            try:
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

              if 'kwd' in inf:
                kwd = inf['kwd']
                if kwd.count('\n') > 2:
                    kwdset = set(entry.strip() for entry in kwd.split('\n'))
                else:
                    kwdset = set(entry.strip() for entry in kwd.split())
              for x in kwdset:
                  words.add(x.strip())
                  
              if 'def' in inf:
                defs = inf['def']
              
              
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

            compressed_content = zlib.compress(file_content)

            if len(pmid) > 10:
                pmids = pmid.split()
                pmids = list(set(pmids))
            else:
                pmids = [pmid]
            
            words2 = kwd.split()
            for w in words2:
                w = w.strip()
                words.add(w)
                
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
                    
            for pmid in pmids:
            # Append the entry to batch data
                if len(pmid) > 4 and len(pmid) < 12:
                    batch_data.append((filename, pmid, compressed_content))

            if len(batch_data) >= BATCH_SIZE:

                print(".",end="")
                cur.executemany('''
                    INSERT OR IGNORE INTO records (id, pmid, content)
                    VALUES (?, ?, ?)
                ''', batch_data)
                conn.commit()  # Commit the transaction
                batch_data.clear()  # Clear the batch data
 
            if len(batch_data_keywords) >= BATCH_SIZE:

                print(".",end="")
                cur_kw.executemany('''
                    INSERT OR IGNORE INTO keywords (keyword, pmid, type)
                    VALUES (?, ?, ?)
                ''', batch_data_keywords)
                conn_kw.commit()  # Commit the transaction
                batch_data_keywords.clear()  # Clear the batch data
             
if batch_data:
    cur.executemany('''
        INSERT OR IGNORE INTO records (id, pmid, content)
        VALUES (?, ?, ?)
    ''', batch_data)
    conn.commit()  
# Commit the final transaction
if batch_data_keywords:
    cur_kw.executemany('''
        INSERT OR IGNORE INTO keywords (keyword, pmid, type)
        VALUES (?, ?, ?)
    ''', batch_data_keywords)
    conn_kw.commit()
# Close the database connection
conn.close()
conn_kw.close()

print("End")

