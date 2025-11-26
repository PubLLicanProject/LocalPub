import requests
import json
import hashlib
import os
import sys
import hashlib
from pathlib import Path

# For downloading locally (NON HPC system or to track downloads through command line prints)
DEBUGMODE = False
MAKELOG = False
PRINTJSON = True
TESTMODE = False

# Url to which the PMC files are downloaded from
BASE_URL="https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
SUM_FILE="sum"
FILETYPE = "json_ascii"

# Python objects to turn to dictionaries
ERRDICT = {}
DLDICT = {}
CORRUPT = {}
EXISDICT = {}

# get the path to where it should be downloaded - if not path specified default to local folder.
if len(sys.argv) > 1:
    # TODO Check if the path is valid path
    PATH_DIR = Path(sys.argv[1])
    PATH_DIR = PATH_DIR.resolve()
    Path(PATH_DIR).mkdir(exist_ok=True)
else:
    PATH_DIR = Path("./pub")
    PATH_DIR = PATH_DIR.resolve()

# --------------------------------------- L O G G I N G - & - M D 5 S U M ---------------------------------------------------------------------------------------------------------

def savelog(code, fileName):
    """ Update the dictionary based on the code below """
    
    match code:
        # download dictionary (DLDICT) codes
        case 100: DLDICT.update({fileName: "Sucessfully downloaded"})
        
        # Existence dictioanry codes (EXISDICT) codes
        case 200: EXISDICT.update({fileName: "Already exists. No Corruption"})
        
        # Cooruption dictionary codes (CORRUPT) codes
        case 300: CORRUPT.update({fileName: "File is corrupted"})
        
        # Error dictionary codes
        case 400: ERRDICT.update({fileName: {"Error": "Failed to download the file"}})
        case 401: ERRDICT.update({fileName: {"Error": f"File not found in {str(PATH_DIR)}"}})
        case 402: ERRDICT.update({fileName: {"Error": "User Interrupted process."}})
        case 404: ERRDICT.update({fileName: {"Error": "Download failed. Connection error"}})
        

def logger():
    """ Log the files in a json format in the chosen directory. """
    obj = {
            "PATH": str(PATH_DIR.absolute().resolve),
            "Downloads": DLDICT,
            "Errors": ERRDICT,
            "Corrupted": CORRUPT,
            "Existing": EXISDICT
        } 
    if PRINTJSON:
        print(json.dumps(obj))
    if MAKELOG:
        with (PATH_DIR / Path("log.json")).open(mode='w') as file:
            json.dump(obj, file)


def md5sumCheck(original_md5, fileName):
    """ Performs md5sum on a file and checks with the original md5 hash"""

    try:
        # Calculate the MD5 on its contents
        with (PATH_DIR / Path(fileName)).open(mode='rb') as file:
            data = file.read()    
            md5_returned = hashlib.md5(data).hexdigest()
    
        # if the md5sum comparison suceeds return 0
        if original_md5 == md5_returned:
            savelog(200, fileName)
            if DEBUGMODE: print(f"{fileName} not corrupted")
            return 0
        else:
            # Log the corrupted file and the wrong md5hash
            if DEBUGMODE: print(f"{fileName} is corrupted")
            savelog(300, fileName)
            return 1
    except FileNotFoundError:
        savelog(401, fileName)

# ---------------------------- P R E L I M I N A R Y - C H E C K -------------------------------------------------------------------------

def updateExistence():
    """ Check for the existence of the update file. 
        The update file states inconsistency of checksum. 
        Therefore it turns off the md5sum checks done.
    """
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
    if (PATH_DIR).exists():
        return md5sumCheck(md5hash, fileName)
    else:
        # Return the result of the md5sum to check if there is corruption
        print(f"{path} not found")
        return 1    

# --------------------------D O W N L O A D I N G - F U N C T I O N S--------------------------------------------------------------------------------------------------------------

def download_sum_file():
    # download file using BASE_URL
    if DEBUGMODE: print("Downloading the sum file...")

    # Create the folder where the the sum file would be stored
    directory = Path(PATH_DIR)
    if not directory.exists():
        directory.mkdir(parents=True, exist_ok=True)

    # read the file from the URL
    with requests.get(BASE_URL + "/" + SUM_FILE) as f:
        # html = f.read().decode('utf-8')
        # save the file into the folder as 'sum'
        with (PATH_DIR / Path(SUM_FILE)).open("w") as file: 
            file.write(f.text)
    
    # Check if the file exists in the created folder
    if not (PATH_DIR / Path("sum")).exists(): 
        savelog(400, "sum.txt")
        return 1
    else:
        savelog(100, "sum.txt")
        if DEBUGMODE: print("Succesfully downloaded")
        return 0

def download_file(url, fileName, md5hash):
    """ Download the file"""
    size = 0
    local_fileName = PATH_DIR / Path(url.split('/')[-1])

    # print the current file being downloaded
    if DEBUGMODE: print(f"Downloading {fileName} {md5hash}")

    try:
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
            with open(local_fileName, 'wb') as f:
                for chunk in r.iter_content(chunk_size=None): 
                    f.write(chunk)
                    size += len(chunk)
                    if DEBUGMODE and length: print('{:.2f}%'.format((size/length)*100), end='\r')
            if DEBUGMODE: print("done")
    
            # Log the file that has been downloaded
            savelog(100, fileName)

            

    except:
        # Log the connection error and put it into the logs
        savelog(404, fileName)


    return local_fileName

def download_and_verify(hash, fileName):
    """ download and verify the files """
    file_path = PATH_DIR / Path(fileName)
    url = BASE_URL + "/" + fileName

    try:
        # Download the file 
        download_file(url, fileName, hash)

        # Perform md5sum and check if file exists.
        if not Path(file_path).exists():
            savelog(401, fileName)
        else:
            # perform md5sum check on the the hash
            md5sumCheck(hash, fileName)

    except KeyboardInterrupt:
        # Exit the Program when keyboard interrupt is pressed and log.
        savelog(402, fileName)
        logger()
        sys.exit()
    


# ----------------------------------------------------------------------------------------------------------------------------

# Function to parse the sum file and download json_unicode files
def parse_sum_file_and_download():
    """ Parse the sum file and download the files inside it"""

    # Create list to download from sum file
    hashAndFile = {}
    with open(PATH_DIR / Path(SUM_FILE), "r") as f:
        for line in f: 
            split = line.split()
            hashAndFile.update({split[0] : split[1]})
 
    # Only include the the fileNames that have json_ascii in them
    for hash, fileName in hashAndFile.copy().items(): 
        if FILETYPE not in fileName: del hashAndFile[hash]

    # Remove uncorrupted existing files from the list to download
    if DEBUGMODE: print("\nPerforming md5sum check.")
    for hash, fileName in hashAndFile.copy().items():
        if check_existing_files(hash, fileName) == 0: del hashAndFile[hash]

    # Print the name and hash of the file if DEBUGMODE
    if DEBUGMODE:
        print("\nFiles to download:")
        for hash, fileName in hashAndFile.copy().items(): 
            print(hash,":", fileName)
        print("\n")

    # Download the files based on the key value pair
    if TESTMODE:
        i = 0
        for hash, fileName in hashAndFile.items(): 
            download_and_verify(hash, fileName)
            if i == 1: break
            i += 1
    else:
        for hash, fileName in hashAndFile.items(): 
            download_and_verify(hash, fileName)

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
