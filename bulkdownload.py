import urllib.request
import requests
import json
import hashlib
import pathlib
import gc
import os
import sys


# For downloading locally (NON HPC system or to track downloads through command line prints)
VERBOSE = True
TEST = False

# Url to which the PMC files are downloaded from
BASE_URL="https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
SUM_FILE="sum"

# Log dictionaries 
ERRDICT = {}
DLDICT = {}
CORRUPT = {}
EXISDICT = {}

FILETYPE = "json_ascii"

# get the path to where it should be downloaded - if not path specified default to local folder.
if len(sys.argv) > 1:
    # TODO Check if the path is valid path
    PATH_DIR = os.path.abspath(sys.argv[1])
    os.makedirs(PATH_DIR, exist_ok=True)
else:
    PATH_DIR = os.getcwd() + "\\pub"

# --------------------------------------- L O G G I N G - & - M D 5 S U M ---------------------------------------------------------------------------------------------------------

def savelog(code, filename):
    """ Update the dictionary based on the code below """
    
    match code:
        # download dictionary (DLDICT) codes
        case 100: DLDICT.update({filename: "Downloaded"})
        
        # Existence dictioanry codes (EXISDICT) codes
        case 200: EXISDICT.update({filename: "Already exists. No Corruption"})
        
        # Cooruption dictionary codes (CORRUPT) codes
        case 300: CORRUPT.update({filename: {"File is corrupted"}})
        
        # Error dictionary codes
        case 400: ERRDICT.update({filename: {"Error": "Failed to download the file"}})
        case 401: ERRDICT.update({filename: {"Error": f"File not found in {PATH_DIR}"}})
        case 402: ERRDICT.update({filename: {"Error": "User Interrupted process."}})
        case 404: ERRDICT.update({filename: {"Error": "Download failed. Connection error"}})
        

def logger():
    """ Log the files in a json format in the chosen directory. """
    with open(f"{PATH_DIR}/log.json", 'w') as file:
        obj = {
            "Errors": ERRDICT,
            "Downloads": DLDICT,
            "Corrupted": CORRUPT,
            "Existing": EXISDICT,
        } 
        json.dump(obj, file)


def md5sumCheck(original_md5, fileName):
    """ Performs md5sum on a file and checks with the original md5 hash"""

    # Import hashlib library (md5 method is part of it)
    import hashlib

    if VERBOSE: print("Performing md5sum check.")

    # Calculate the MD5 on its contents
    with open(fileName, 'rb') as file:
        data = file.read()    
        md5_returned = hashlib.md5(data).hexdigest()

    # if the md5sum comparison suceeds return 0
    if original_md5 == md5_returned:
        savelog(200, filename)
        return 0
    else:
        # Log the corrupted file and the wrong md5hash
        savelog(300, filename)
        return 1

# ---------------------------- P R E L I M I N A R Y - C H E C K -------------------------------------------------------------------------

def updateExistence():
    """ Check for the existence of the update file. 
        The update file states inconsistency of checksum. """
    url = BASE_URL + "/update.txt"
    
    try:
        r = requests.head(url)
        if r.status_code > 400 or r.status_code < 600: 
            return 1
        else:
            return 0
    except requests.ConnectionError:
        return 1

def sumnewExs():
    """ Check the existence of the sum-new file """
    url = BASE_URL + f"/sum-new.txt"
    try:
        r = requests.head(url)
        if r.status_code > 400 or r.status_code < 600:  
            return 1
        else:
            return 0
    except requests.ConnectionError:
        return 1

def check_existing_files(md5hash, fileName):
    """ Check if the file already exists, and check for corruption"""

    # Check if the file already exists in the chosen directory
    if os.path.exists(PATH_DIR + fileName): 
        return md5sumCheck(md5hash, fileName)
    else:
        # Return the result of the md5sum to check if there is corruption
        return 1

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def download_sum_file():
    # download file using BASE_URL
    if VERBOSE: print("Downloading the sum file...")

    # Create the folder where the the sum file would be stored
    directory = pathlib.Path(PATH_DIR)
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)

    # read the file from the URL
    with urllib.request.urlopen(BASE_URL + "/" + SUM_FILE) as f:
        html = f.read().decode('utf-8')
        # save the file into the folder as 'sum'
        with open(PATH_DIR +"/"+ SUM_FILE, "w") as file: file.write(html)
    
    # Check if the file exists in the created folder
    if not os.path.exists(f"{PATH_DIR}/sum"): 
        savelog(400, "sum.txt")
        return 1
    else:
        savelog(100, "sum.txt")
        if VERBOSE: print("Succesfully downloaded")
        return 0

def download_file(url, file_name, md5hash):
    """ Download the file"""
    size = 0
    local_filename = PATH_DIR +"/"+ url.split('/')[-1]

    # print the current file being downloaded
    if VERBOSE: print(f"Downloading {file_name} {md5hash}")

    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()

        # get the total length of the file and create block size
        length = r.headers.get("Content-Length")
        if length:
            length = int(length)
            blocksize = max(4096, length//100)
        else:
            # Assumes this is being ran in an HPC
            blocksize = 1000000

        # Write to file in chunks and update the progress bar
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=None): 
                f.write(chunk)
                size += len(chunk)
                if VERBOSE and length: print('{:.2f}%'.format((size/length)*100), end='\r')

        # Log the file that has been downloaded
        savelog(100, filename)
        #DLDICT.update({md5hash: file_name})
        if VERBOSE: print("done")


    return local_filename

def download_and_verify(hash, filename):
    """ download and verify the files """
    file_path = PATH_DIR + filename
    url = BASE_URL + "/" + filename

    try:
        # Download the file 
        download_file(url, filename, hash)

        # Perform md5sum and check if file exists.
        if not pathlib.Path(file_path).exists():
            savelog(401, filename)
        else:
            # perform md5sum check on the the hash
            md5sumCheck(hash, file_path)

    except KeyboardInterrupt:
        # Exit the Program when keyboard interrupt is pressed and log.
        savelog(402, filename)
        logger()
        sys.exit()
    except:
        # Log the connection error and put it into the logs
        savelog(404, filename)


# ----------------------------------------------------------------------------------------------------------------------------

# Function to parse the sum file and download json_unicode files
def parse_sum_file_and_download():
    """ Parse the sum file and download the files inside it"""

    # Create list to download from sum file
    hashAndFile = {}
    with open(PATH_DIR + f"/{SUM_FILE}", "r") as f:
        for line in f: 
            split = line.split()
            # Check if file exists and if there is corruption
            if check_existing_files(split[0], f"{PATH_DIR}/{split[1]}") == 1:
                hashAndFile.update({split[0] : split[1]})
            else:
                # Log that file exists and has no corruption
                savelog(200, split[1])
    
    # Only include the the filenames that have json_ascii in them
    for hash, filename in hashAndFile.copy().items(): 
        if FILETYPE not in filename: del hashAndFile[hash]

    # Print the name and hash of the file if verbose
    if VERBOSE:
        for hash, filename in hashAndFile.copy().items(): 
            print(hash,":", filename)

    # Download the files based on the key value pair
    if TEST:
        i = 0
        for hash, filename in hashAndFile.items(): 
            download_and_verify(hash, filename)
            if i == 2: break
            i += 1
    else:
        for hash, filename in hashAndFile.items(): 
            download_and_verify(hash, filename)

# ------------------------------ M A I N ---------------------------------------------

def main():
    # preliminary check for update.txt and sum-new.txt
    md5mode = updateExistence()
    sumnewCode = sumnewExs()

    # first download the sum file
    download_sum_file()

    # Then parse the sum file and download
    parse_sum_file_and_download()

    # Log the downloaded, existing, and corrupted files. 
    logger()

main()
