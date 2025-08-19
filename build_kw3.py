import sys
import sqlite3
import tarfile
import zlib
import json
import re
import warnings
import platform
import shutil
import subprocess
import platform
import concurrent.futures


#CONSOLIDATE_FILE just matches up the keywords after sorting
#not essential - but if done here then it is parallelised
#and reduces some disk space prior to the merge
#could also run separately, but this may slightly spread out the disk usage over time
from consolidate import consolidate
CONSOLIDATE_FILE = False

executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)  # 1 ensures sequential execution
futures = []  # Track all sorting tasks


BATCH_SIZE = 1024*256

# Suppress all DeprecationWarnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

#sections = {'DISCUSS', 'APPENDIX', 'CASE', 'ACK_FUND', 'SUPPL', 'REF', 'FIG', 'TABLE', 'ABSTRACT', 'INTRO', 'ABBR', 'RESULTS', 'TITLE', 'KEYWORD', 'CONCL', 'COMP_INT', 'METHODS'}

 
#about 40 million lines per gb
#20gb gives us ~100 files (and should be easily sortable)
MAX_LINES = 10*40*1000*1000
 
ALL_SECTIONS = False 
CONSECUTIVE_WORDS = 5
SUFFIX = '_kw_5.txt'
found_sections = set()
sort_failed = 0

def generate_consecutive_word_groups(words, n):
    """
    Generate consecutive groups of n words from a list.
    :param words: List of words
    :param n: Number of words in each group
    :return: List of tuples, each containing n consecutive words
    """
    return [' '.join(words[i:i + n]) for i in range(len(words) - n + 1)]
    
#trying to execute in parallel, it may be beneficial - although disk I/O is still likely the problem

def sort_file(file_write_name):
    # return sort_file_parallel(file_write_name)
    future = executor.submit(sort_file_parallel, file_write_name)
    futures.append(future)

def wait_for_all_sorts():

    concurrent.futures.wait(futures)
    print("All sorting tasks have completed.")
    

def remerge_files(outputfile,files):
    
    sopt = "--temporary-directory=/mnt/hc-storage/users/tony/tmp"
    command = ["sort", sopt, "-m", "-o", outputfile]
    for f in files:
        command.append(f)

    if platform.system() == "Linux":
        command.insert(1, "--parallel=8")
    print("start merge sort",outputfile)
    result = subprocess.run(command, env={'LC_ALL': 'C'}, check=True)     
    for file in files:
        shutil.move(file, "./old/"+file)
        
 
def sort_file_parallel(file_write_name):
    temp_file_name  = file_write_name+"_sorted"
    # need to sort so that merging can take place efficiently
    sopt = "--temporary-directory=/mnt/hc-storage/users/tony/tmp"
    command = ["sort", sopt, "-o", temp_file_name, file_write_name]

    if platform.system() == "Linux":
        command.insert(1, "--parallel=8")
    print("start sort",file_write_name)
    result = subprocess.run(command, env={'LC_ALL': 'C'}, check=True)
    if result.returncode == 0:
        print("sort complete")
        shutil.move(temp_file_name, file_write_name)
        if CONSOLIDATE_FILE:
            consolidate(file_write_name)
            print("consolidate complete")
    else:
        shutil.move(file_write_name,file_write_name+"_unsorted")
        sort_failed += 1
        print("NOT SORTED, DO NOT USE")
        return 1
    return 0
    
    
    
    
stopwords = set(["i", "me", "my", "myself", "we", "our", "ours", "ourselves", "you", "your", "yours", "yourself", "yourselves", "he", "him", "his", "himself", "she", "her", "hers", "herself", "it", "its", "itself", "they", "them", "their", "theirs", "themselves", "what", "which", "who", "whom", "this", "that", "these", "those", "am", "is", "are", "was", "were", "be", "been", "being", "have", "has", "had", "having", "do", "does", "did", "doing", "a", "an", "the", "and", "but", "if", "or", "because", "as", "until", "while", "of", "at", "by", "for", "with", "about", "against", "between", "into", "through", "during", "before", "after", "above", "below", "to", "from", "up", "down", "in", "out", "on", "off", "over", "under", "again", "further", "then", "once", "here", "there", "when", "where", "why", "how", "all", "any", "both", "each", "few", "more", "most", "other", "some", "such", "no", "nor", "not", "only", "own","using","used","among","may", "same", "so", "than", "too", "very", "s", "t", "can", "will", "just", "don", "should", "now", "were", ])

more_stopwords = set(["across","addition","additional","also","Although","approach","available","based","changes","collected","common", "compared","conducted","considered","consistent","control","could","current","data","defined", "described","determine","determined","differences","different","due","effect", "effects","either","even","example","findings","first","following","found","given", "group","groups","high","higher","However","identify","important","include", "included","including","increase","increased","individual","information","known","large", "least","less","level","levels","likely","limited","low","lower", "many","need","needed","new","number","obtained","often","one","overall", "part","per","performed","possible","potential","present","previous","previously","provide", "provided","range","recent","related","report","represent","required","respectively","response", "result","sample","several","show","showed","shown","significant","significantly","similar", "single","size","small","specific","standard","test","three","time","total", "two","type","use","values","well","whether","within","without","work","would" ])

#load_stopwords() 
import unicodedata
import codecs

def decode(text):
 
    # Step 1: Decode escaped sequences (e.g., "\xE9" → "é", "\u00E9" → "é")
    text = codecs.decode(text, "unicode_escape", errors='ignore')


    # Step 2: Normalize and convert Unicode characters to ASCII (e.g., "é" → "e")
    text = unicodedata.normalize('NFKD', text).encode('ascii', 'ignore').decode('ascii', errors='ignore')

  
    return text
 
def decode_old(text):
  
 
    return text.encode().decode("unicode_escape", errors='ignore')
  
# Decode the cleaned text
    


def load_stopwords():
    file_path = "words_10k.txt"  # Replace with your file path

    
    with open(file_path, 'r') as file:
        # Iterate through each line in the file
        for line in file:
            # Strip leading/trailing whitespace (like newlines) and process the line
            word = line.strip()
            stopwords.add(word)



 
trim_pattern = re.compile(r"^[\s.,:;!?\"']+|[\s.,:;!?\"']+$")

def trim_tokens(tokens):
    # Use precompiled regex for efficiency
    return [trim_pattern.sub("", token) for token in tokens if token]

def split_text(kwd):
    #kwd =  re.sub(r"[\[\]\{\}\(\)\'\"]", "", kwd)
    kwd =  re.sub(r"[\[\]\{\}\(\)\"]", "", kwd)
    words1 = kwd.split()
    words1 = trim_tokens(words1)
    return words1



def split_text_w_seps(kwd):
    #kwd =  re.sub(r"[\[\]\{\}\(\)\'\"]", "", kwd)
    kwd =  re.sub(r"[\[\]\{\}\(\)\"]", "", kwd)
    words1 = re.split(r"[\s\/\.\-]+", kwd)  # Split on space, /, ., and -

    words1 = trim_tokens(words1)
    return words1
    

        
tar_file_path = 'PMC000XXXXX_json_unicode.tar.gz'
if len(sys.argv) > 1:
    tar_file_path = sys.argv[1]

# Create SQLite database connection (or connect to an existing one)

file_lines = 0
file_list = []
file_count = 0
file_suffix = "_"+str(file_count)+"_"
 
file_write_name = tar_file_path+file_suffix+SUFFIX
final_file_name = tar_file_path+SUFFIX

file_write = open(file_write_name,"w")
file_list.append(file_write_name)

batch_data = []
batch_data_keywords = []

# Set batch size  


word_counts = {}
# Path to your .tar.gz file
total_words = 0
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

             
            pmid = filename
            kwd=""
            kwdset = set()
            words = {}
            abstract=""
            try:
              content_text = file_content.decode('utf-8')
              
              
              
              
              #exit(1)
              
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
                    #not sure this works with ascii
                    kwdset = set(entry.strip() for entry in kwd.split('\n'))
                else:
                    kwdset = set(entry.strip() for entry in kwd.split())
              for x in kwdset:
                  x = decode(x)
                  x = x.strip()
                  if x not in words:
                        words[x] = 0
                  words[x] = words[x] + 1
                  
              if 'def' in inf:
                defs = inf['def']
              
              
              sections = ["INTRO","METHODS","DISCUSS","ABSTRACT","TITLE","TABLE","FIG","RESULTS","CONCL","ABBR","KEYWORD","CASE","APPENDIX"]
              #all_sections = ['COMP_INT', 'SUPPL', 'AUTH_CONT', 'REVIEW_INFO', 'REF', 'RESULTS', 'TABLE', 'ACK_FUND', 'CASE', 'KEYWORD', 'TITLE', 'FIG', 'CONCL', 'ABBR', 'DISCUSS', 'METHODS', 'INTRO', 'APPENDIX', 'ABSTRACT']

              
              
              bad_sections = ["ACK_FUND","REF"]

              pmid = pmid.strip()
              for passage in p:
                inf = passage['infons']
                if "section_type" in inf:
                    st = inf["section_type"]
                    if 'text' in passage:
                        found_sections.add(st)
                        if ALL_SECTIONS or st in sections:
                            if st not in bad_sections:
                                passage_text = decode(passage['text'])
                                

                                abstract += " "+passage_text+ "\n\n"

              kwd = defs+" "+ abstract
              
            except Exception as e:
              print("error",e)
              pass

 
            if len(pmid) > 10:
               #some are more than one
                
                pmids = pmid.split()
                pmids = list(set(pmids))
                if len(pmids) > 1:
                    print(pmid)      
            else:
                pmids = [pmid]
            
       #remove 
            words1 = split_text(kwd)
            words2 = split_text_w_seps(kwd)
            
            for w in words1:
                w = w.strip()
                if w not in words:
                    words[w] = 0
                words[w] = words[w] + 1
 
            
            for l in range(2,CONSECUTIVE_WORDS+1):
                words3 = generate_consecutive_word_groups(words2,l)
                for w in words3:
                    w = w.strip()
                    if w not in words:
                        words[w] = 0
                    words[w] = words[w] + 1

                
            for pmid in pmids:
                #print("adding ",len(words)," for ",pmid)
                
                for word in words:
                  wordcount = words[word]
                  word =word.strip()
                  parts = word.split()
                  
                  stopWord = True
                  for p in parts:
                      if p.lower() not in stopwords:
                          stopWord = False

                  if len(word) > 1 and not stopWord:
            # Append the entry to batch data
                    if len(word) > 2:
                        kwtype = 0
                        if word in kwdset:
                            kwtype = 1
                        if " " not in word:
                            #trying to handle hyphenated words by also removing hyphens
                            if "-" in word:
                                wordh = word.replace("-", "")
                                batch_data_keywords.append((wordh, pmid, wordcount ))
                             
                            
                            word1 = re.split(r"[\/\.\-]+\:", word)
                          #  print("splitting",word1)
                            if len(word1) > 1:
                                for w in word1:
                                    w = w.strip()
                                    if len(w) > 2:
                           #             print("adding",w)
                                        batch_data_keywords.append((w, pmid, wordcount ))

                        
                        word=" ".join(word.split()) 
                        batch_data_keywords.append((word, pmid, wordcount ))
                        
                
 
 
            if len(batch_data_keywords) >= BATCH_SIZE:

                file_write.writelines(f"{word}\t{pmid}\t{wordcount}\n" for word, pmid, wordcount in sorted(batch_data_keywords))
                print(".",end="")
                file_lines += len(batch_data_keywords)

                batch_data_keywords.clear()  # Clear the batch data
             
             
                if file_lines > MAX_LINES:
                    file_write.close()
                    file_lines = 0
                    file_count += 1
                    file_suffix = "_"+str(file_count)+"_"

                    
                    sort_file(file_write_name)
                    
                    
#                    if file_count > 3:
#                        break                   
                    
                    
                    file_write_name = tar_file_path+file_suffix+SUFFIX
                    file_write = open(file_write_name,"w")
                    file_list.append(file_write_name)
                    print("new write",file_write_name)
                    

                    
 
# write any final keywords
if batch_data_keywords:
    file_write.writelines(f"{word}\t{pmid}\t{wordcount}\n" for word, pmid, wordcount in sorted(batch_data_keywords))

 
file_write.close()

sort_file(file_write_name)
#        exit(1)


#for file_write_name in file_list:
#    sort_file(file_write_name)



    
wait_for_all_sorts()            
if sort_failed > 0:
    print("Sort Failed - check files")
    exit(1)

print("attempt remerge")
remerge_files(final_file_name,file_list)
        
print(found_sections)
 
