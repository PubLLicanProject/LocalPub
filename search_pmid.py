import sys
import sqlite3
import json
import os
import json
import struct
import re
#import base64
import shlex
#input is a string, either a pubmed id in numberical form
#or a pubemd central id, beginning PMC
#returns a string as the json of  the publication
#returns an empty list if no id found
import binascii


wildcard = False
count_only = False
add_plural = False
ignore_case = True
and_mode = False

#only needed for pyinstaller version
def get_base_path():
    if getattr(sys, 'frozen', False):  # Check if the app is "frozen" (bundled)
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

DB_FILE = get_base_path()+'/'+'pmc_kw5.db'

def decompress(blob):
    """Retrieves a list of PMID strings from a BLOB."""
    
    if not blob:
        return []

#Note - pubmed IDs are not large enough to ever do this - it would need to be at least 10 digits
    data = blob
    

    # Unpack integers
    int_list = list(struct.unpack(f"{len(data) // 4}i", data))

    # Convert back to string format
    pmids = [f"PMC{-x}" if x < 0 else str(x) for x in int_list]

    return pmids
    
def get_keyword(keywords, db_file = DB_FILE, keytype = None):

    global wildcard, count_only, add_plural, ignore_case, and_mode 
   
 
    try:    
        conn = sqlite3.connect(f"file:{db_file}?mode=ro", uri=True)
    except:
         print(f"['Error : no database file {db_file}]")
         return set()


    cur = conn.cursor()
 
  
 

    output = []

#numerical is a pubmed id
#beginning with PMC is a  PMC id
    select = "pmid"
#    if (count_only):
#        select = "count (distinct pmid)"
 
    
    if ignore_case:
        keywords = [term.lower() for term in keywords]
    if add_plural:
        # Adds an 's' as an optional ending to each term
        keywords = keywords+ [term + 's' for term in keywords]
 
        
 
    junction = " OR "
 
    params = [term for term in keywords]

    search_cond = "="
    if wildcard:
        search_cond = "LIKE"
 
    if ignore_case:
        search_cond = " COLLATE NOCASE "+search_cond 

    query = "SELECT "+select+" FROM keywords WHERE " + junction.join(["keyword "+search_cond+" ? " for _ in keywords])  
 
 
 
    # Execute the query

    cur.execute(query, params)   
 
 
    rows = cur.fetchall()
    output = set()
    for row in rows:
        
        outrow = row[0]
        
        #       outrow = zlib.decompress(row[0]).decode('utf-8')
        outrow = decompress(outrow)
#        outrow = outrow.split(",")
        for pmid in outrow:
            output.add(pmid)
    
    
    #output = list(output)  
    conn.close()
   
 
   
    return output
 
 
import sys

def precedence(op):
    """Defines precedence levels for operators."""
    return {"not": 3, "and": 2, "or": 1}.get(op.lower(), 0)
def infix_to_postfix(intokens):
    """Converts infix expression to postfix using the shunting-yard algorithm."""
    output = []
    stack = []
    tokens = []
    concnt = 0
    for token in intokens:
             if token.lower() in {"and", "or", "not"}:
                 concnt += 1

    for i in range(0,len(intokens)):
        token = intokens[i]
        #If no boolean is selected, we assume 'or' (as that is easiest)
        if concnt == 0:
            if i > 0:
               last = intokens[i-1]
               if token.lower() not in {"and", "or", "not", "(", ")"}:  
                    if last.lower() not in {"and", "or", "not", "("}:   
                        tokens.append("or")
        tokens.append(token)
        
    for token in tokens:
        if token.lower() in {"and", "or", "not"}:  # Only case-convert for operators
            while stack and precedence(stack[-1]) >= precedence(token.lower()):
                output.append(stack.pop())
            stack.append(token)
        elif token == "(":
            stack.append(token)
        elif token == ")":
            while stack and stack[-1] != "(":
                output.append(stack.pop())
            stack.pop()  # Remove '('
        else:
            output.append(token)

    while stack:
        output.append(stack.pop())

    return output

def evaluate_postfix(words, dbfile):
    expression = infix_to_postfix(words)
    
    stack = []
    positive_keywords = set()

    # Helper function to convert term or term lists to result sets
    def to_result(item):
        if isinstance(item, str):
            return get_keyword([item], dbfile)
        elif isinstance(item, list):
            return get_keyword(item, dbfile)
        return item  # Already a result set

    for token in expression:
        if token.lower() not in {"and", "or", "not"}:
            positive_keywords.add(token)
            stack.append(token)
            
        elif token.lower() == "or":
            right = stack.pop()
            left = stack.pop()
            
            # If both can be represented as terms, collect them
            if all(isinstance(x, (str, list)) for x in [left, right]):
                left_list = [left] if isinstance(left, str) else left
                right_list = [right] if isinstance(right, str) else right
                stack.append(left_list + right_list)
            else:
                # At least one is a result set
                stack.append(to_result(left) | to_result(right))
            
        elif token.lower() == "and":
            right = stack.pop()
            left = stack.pop()
            stack.append(to_result(left) & to_result(right))
            
        elif token.lower() == "not":
            operand = stack.pop()
            if not stack:
                return set()

            prev = stack.pop()
            stack.append(to_result(prev) - to_result(operand))
    

    return to_result(stack[0])
        
        
        
def evaluate_postfix_previous(words, dbfile):
    
    isBoolean = False
    for token in words:
        if token.lower() in {"and", "or", "not"}:
            isBoolean = True
            
    if isBoolean == False:
        return get_keyword(words,dbfile)
            
            
    expression = infix_to_postfix(words)
    
    """Evaluates a postfix expression using a stack."""
    stack = []
    positive_keywords = set()

    for token in expression:
        if token.lower() in {"and", "or", "not"}:
            if token.lower() == "not":

                operand = stack.pop()
                #tried doing a not without anything before it
                if not stack:
                    return set()
                stack.append(stack.pop() - operand)  # Subtract results from last positive set
 
            else:
                right = stack.pop()
                left = stack.pop()
                stack.append(left & right if token.lower() == "and" else left | right)
        else:
            positive_keywords.add(token)
            stack.append(get_keyword([token],dbfile))
 
    return stack[0] if stack else set()

def custom_sort(article):
    if article.isdigit():  # Check if the article is a numeric string
        return (2, int(article))  # Numbers should come first, sorted in reverse order
    else:
        # Extract the number after "PMC" using regular expression
        match = re.match(r"PMC(\d+)", article)
        if match:
            return (1, int(match.group(1)))  # PMC strings should come after numbers, sorted by the number
        return (0, 0)  # If it's neither a number nor a "PMC" string, put it at the end (just in case)


 
def process_input(words):
    output = []
    
    
    try:
        result = evaluate_postfix(words,DB_FILE)  # Evaluate postfix expression
        output = list(result)
    except ValueError as e:
        print(f"Error: {e}")
 
  
    output =  list(set(output))
    
        
    output.sort(key=custom_sort, reverse=True)
    return output
    
def b64decode(data):
    missing_padding = len(data) % 4
    if missing_padding:
        data += '=' * (4 - missing_padding)  # Fix padding if needed
    return binascii.a2b_base64(data)
  
def decode_arguments():
    if '-b' in sys.argv:
        idx = sys.argv.index('-b')
        if idx + 1 < len(sys.argv):
            encoded_string = sys.argv[idx + 1]
            
            decoded_string =b64decode(encoded_string).decode('utf-8')
            decoded_args = shlex.split(decoded_string)
            sys.argv = [sys.argv[0]] + decoded_args  # Keep the script name as the first element



def main():
    global wildcard, count_only, add_plural, ignore_case, and_mode  , DB_FILE

    decode_arguments()
    #give an empty answer if no input specified
    keyword = ""

    if len(sys.argv) < 2:
        print("Usage: search_pmid keyword or \"key word phrase\"  \n options\n -f <filename> select database file - default is pmc_kw.db\n -csv output as csv  (default json)\n -p plural - also adds an 's' \n -w allow SQL wildcards (e.g. %) \n -s case sensitive search \n -a changes OR to AND  ) -c print count only\n\n examples: search_pmid plasmodium \n search_pmid plasmodium malaria -a -c \n search_pmid PF3D7% -w -c \n search_pmid \"plasmodium falciparum\" -c \n")
        return(0)
    if len(sys.argv) > 1:
        keyword = sys.argv[1]
     
    keytype = None
    csvOut = False

    words = []

    one_line = False
    for x in range(1, len(sys.argv)):
            
        if sys.argv[x-1] == "-f":
            DB_FILE = sys.argv[x]
            continue

        if sys.argv[x] == "-csv":
            csvOut = True

        if sys.argv[x] == "-c":
            count_only = True
        if sys.argv[x] == "-p":
            add_plural = True
        if sys.argv[x] == "-a":
            and_mode = True

        if sys.argv[x] == "-w":
            wildcard = True
            add_plural = False

        if sys.argv[x] == "-s":
            ignore_case = False
        if sys.argv[x] == "-o":
            one_line =  True
            
        if sys.argv[x][0] == "-":
            continue
            
        words.append(sys.argv[x])
        

    if len(words) == 0:
        print("[]")
        return(1)
        
    output = process_input(words)
    
    if count_only:
        print(len(output))
    else: 
        if csvOut: 
            print("pubmed_id")
            for x in output:
                print(x)
        else:
            if one_line:
                json_output = json.dumps(output)
            else:
                json_output = json.dumps(output, indent=4)
            print(json_output) 
    #usage
    #search_pmid.py <searchteam>
    #optional
    #-f filename - to specify a database file
    #-y type - 0 for abstract only, 1 for keyword only
main()
