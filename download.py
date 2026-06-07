import requests
import argparse
import hashlib
import sys
import json
from pathlib import Path

base_url = "https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
BLOCK_SIZE = "auto"
log = {"Path":{}, "Downloads":{},"Errors":{},"Corrupted":{},"Existing":{}}


def updateLog(code, fileName):
    """ Used for crating the json output for pipeline"""
    match code:
        case 000: log["Path"].update({"Path":fileName})
        case 100: log["Downloads"].update({fileName: "Sucessfully downloaded"})
        case 200: log["Existing"].update({fileName: "Already exists. No corruption"})
        case 300: log["Corrupted"].update({fileName: "File is corrupted"})
        case 400: log["Errors"].update({fileName: {"Error": "Failed to download the file"}})
        case 401: log["Errors"].update({fileName: {"Error": "File was not found in user specified path"}})
        case 402: log["Errors"].update({fileName: {"Error": "User Interrupted process."}})
        case 404: log["Errors"].update({fileName: {"Error": "Download failed. Connection error."}})

   
def download(file, path=".", verbose=True):
    """ download a file to the given path"""
    try:
        with requests.get(f"{base_url}/{file}", stream=True) as r:
            r.raise_for_status()
            length = int(r.headers.get("Content-Length"))
            chunk_size = calcChunk(length, BLOCK_SIZE)
            size = 0
            
            # write to file in chunks
            with (Path(path).resolve()/Path(file)).open(mode='wb') as f:
                for chunk in r.iter_content(chunk_size=chunk_size): 
                    f.write(chunk)
                    size += len(chunk)
                    if verbose and length: 
                        print('\r{:.2f}%'.format((size/length)*100), end='\r', flush=True)
                        sys.stdout.flush()
                if verbose: 
                    sys.stdout.write("\rdone" + " " * 10)     
                    sys.stdout.flush()
        
        updateLog(100, file)
        
        return True
                    
    except KeyboardInterrupt:
        updateLog(402)
        if not verbose: print(json.dumps(log, indent=4))
        sys.exit()
    except:
        updateLog(400)
        return False


def calcChunk(length, blocksize):
    # Handle block sizes
    if length and blocksize == "auto":
        length = int(length)
        return max(4096, length//100)
    elif length and isinstance(blocksize , int):
        return blocksize
    else:
        return 1000000


def getsum():
    """ Return a dictionary of the sum file format: {md5hash:filename}"""
    sum = {}
    r = requests.get(f"{base_url}/sum")
    for line in r.text.split("\n"):
        splitt = line.split()
        if splitt: sum.update({splitt[0]:splitt[1]})
    return sum  


def md5sum(md5hash, file, verbose=True):
    """ Calculate md5hash of file and verify integrity"""
    try:
        with Path(file).resolve().open(mode='rb') as f:
            data = f.read()
            md5new = hashlib.md5(data).hexdigest()
            
            if md5hash == md5new:
                return True
            else:
                return False
    except KeyboardInterrupt:
            # Exit the Program when keyboard interrupt is pressed and log.
            updateLog(402, fileName)
            if not verbose: print(json.dumps(log, indent=4))
            sys.exit(1)
    except Exception as e:
        print(e)
 
 
def checkExistence(fileName):
    url = base_url + "/" + fileName
    
    try:
        r = requests.head(url)
        if r.status_code > 400 or r.status_code < 600:
            return False
        else:
            return True
    except requests.ConnectionError:
        return False 


def check_existing_files(md5hash, file, md5mode=True, verbose=True):  
    # Check if the file already exists in the chosen directory
    if (Path(file).resolve()).exists():
        if md5mode:
            mode = md5sum(md5hash, file)
            if mode:
                if verbose: print(f"{file.split("/")[-1]} exists, and is not corrupted")
                updateLog(200, file.split("/")[-1])
                return mode
            else:
                if verbose: print(f"{file.split("/")[-1]} exists, but is corrupted")
                return mode
                
        else:
            if verbose: print(f"{file.split("/")[-1]} exists")
            return True
    else:
        if verbose: print(f"{file.split("/")[-1]} does not exist")
        return False


def bulkdownload(path="./pub", filetype="json_ascii", md5mode=True, verbose=True, test=False):
    
    updateLog(000, path)
    hashAndFile = getsum()
    
    # create directory if not yet created
    Path(path).mkdir(exist_ok=True)
    
    # Only include the the fileNames that have filetype argument in them.
    for hash, fileName in hashAndFile.copy().items(): 
        if filetype not in fileName: del hashAndFile[hash]
        
    # remove uncorrupted files from download dictionary
    for hash, fileName in hashAndFile.copy().items():
        if check_existing_files(md5hash=hash, file=f"{path}/{fileName}", md5mode=md5mode, verbose=verbose):
            del hashAndFile[hash]

    if verbose: print("\nPerforming Bulk download of all tar files that do not exist or is corrupted")
    # download all the files in the dictionary
    
    try:
        for hash, fileName in hashAndFile.items(): 
            # Download the file 
            if verbose: print(f"Downloading {fileName}")
            download(fileName, path=path, verbose=verbose)
    
            # Perform md5sum and check if file exists.
            if not (Path(path + "/fileName").resolve()).exists():
                updateLog(401, fileName)
            elif md5mode:
                # perform md5sum check on the the hash
                if md5sum(hash, f"{path}/{fileName}", verbose=verbose):
                    updateLog(100, fileName)
                else:
                    updateLog(300, fileName)
            if test: break
    
    except KeyboardInterrupt:
        # Exit the Program when keyboard interrupt is pressed and log.
        updateLog(402, fileName)
        if verbose: print("\n",json.dumps(log, indent=4))
        sys.exit(1)
    except Exception as e:
        updateLog(401, fileName)
        



if __name__ == "__main__":
    parser = argparse.ArgumentParser(
    prog='python download.py',
    description = """ Tools for https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC.
                      For list of available files. Use the aforementioned link or type ls.
                      Functionalities of the tools are listed in the options below.
                  """
    )
    
    # option and constraints
    parser.add_argument('-l', action='store_true', help="list the downloadable files. Outputs list in a json 'md5hash':'fileName'")
    parser.add_argument('-p', metavar=("[directory]"), type=str, nargs=1, help="for pipeline use. download all PMC tar files into a folder and prints a json in stdout.")
    parser.add_argument('-d', metavar=("[file]","[path]"), type=str, nargs=2, help="download a file from the link into a folder(path).")
    parser.add_argument('-b', metavar=("[directory]"), type=str, nargs=1, help="download all PMC tar files on the specified directory.")
    parser.add_argument('-m', metavar=("[md5hash]", "[file]"), type=str, nargs=2, help="Check if file exists. Then, verify file integrity using md5hash.")
    args = parser.parse_args()
    
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(1)
 
    cliArgs = vars(args)
    for key, value in cliArgs.copy().items():
        if cliArgs[key] != False and cliArgs[key] != None: 
            op = key

    match op:
        case "l": # Get the sum file and print it out in json {hash:filename}
            print(f"\n{" "*15} md5hash {" "*15}| {" "*8}FileName\n")
            print(json.dumps(getsum(), indent=4))

        case "d": # download a file with its filename
            flag = False
            updateLog(000, str(Path(args.d[1]).resolve()))
            hashAndFile = getsum()
            
            # Check if file exists and determine whether to calculate md5hash
            if args.d[0] in ["README.txt", "pmc.key", "pmc_ascii.key", "pubmed.key", "sum", "sum-new", "update.txt"]:
                print("Checking if file exists.")
                flag = check_existing_files(args.d[0], f"{args.d[1]}/{args.d[0]}", md5mode=False, verbose=True)
            else:
                # if one of the files from the sum file
                print("Checking if file exists and if there is corruption.")
                for key, value in hashAndFile.items():
                    if hashAndFile[key] == args.d[1]:
                        flag = check_existing_files(key, file, md5mode=True, verbose=True)

            if flag:
                updateLog(200, args.d[0])
            else:
                print(f"downloading {args.d[0]}")
                download(args.d[0], path=args.d[1])
            
            print("\n",json.dumps(log, indent=4))
            
        case "b": # bulk download files into a directory
            try:
                print(f"\nChecking existing PMC files in {args.b[0]}")
                if checkExistence("update") or checkExistence("sum-new"):
                    md5mode = False
                else:
                    md5mode = True
                bulkdownload(path=args.b[0], filetype="json_ascii", md5mode=md5mode)
                print("\n",json.dumps(log, indent=4))
            except KeyboardInterrupt:
                # Exit the Program when keyboard interrupt is pressed and log.
                print("\n",json.dumps(log, indent=4))
                sys.exit(1)

        case "m": # calculate md5sum of a file and compare with md5 passed as param
            check_existing_files(args.m[0], args.m[1], md5mode=True, verbose=True)
            
        case "p": # perform bulk download for pipeline and log
            if checkExistence("update") or checkExistence("sum-new"):
                md5mode = False
            else:
                md5mode = True
            bulkdownload(path=args.p[0], filetype="json_ascii", md5mode=md5mode, verbose=False)
            print(json.dumps(log, indent=4))
