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

# Url to which the PMC files are downloaded from
BASE_URL="https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
SUM_FILE="sum"

# Log dictionaries 
ERRDICT = {}
DLDICT = {}
CORRUPT = {}
EXISDICT = {}


# get the path to where it should be downloaded - if not path specified default to local folder.
if len(sys.argv) > 1:
    PATH_DIR = sys.argv[0]
else:
    PATH_DIR = "./pub"

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def md5sumCheck(original_md5, fileName):
    """ Performs md5sum on a file and checks with the original md5 hash"""

    # Import hashlib library (md5 method is part of it)
    import hashlib

    # Calculate the MD5 on its contents
    with open(fileName, 'rb') as file:
        data = file.read()    
        md5_returned = hashlib.md5(data).hexdigest()

    # if the md5sum comparison suceeds return 0
    if original_md5 == md5_returned:
        return 0
    else:
        # Log the corrupted file and the wrong md5hash
        CORRUPT.update({md5_returned : fileName})
        return 1

def check_existing_files(md5hash, fileName):
    """ Check if the file already exists, and check for corruption"""

    # Check if the file already exists in the chosen directory
    if not os.path.exists(PATH_DIR + fileName): 
        return 1
    else:
        # Return the result of the md5sum to check if there is corruption
        return md5sumCheck(md5hash, fileName)


def logger():
    """ Log the files in a json format in the chosen directory"""
    with open(f"{PATH_DIR}/log.json", 'w') as file:
        obj = {
            "ERRDICT": ERRDICT,
            "DLDICT": DLDICT,
            "CORRUPT": CORRUPT,
            "EXISDICT": EXISDICT,
        }
        json.dump(obj, file)


# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def download_file(url, file_name, md5hash):
    """ Download the file"""
    size = 0
    local_filename = PATH_DIR +"/"+ url.split('/')[-1]

    # print the current file being downloaded
    if VERBOSE: print(f"{md5hash} {file_name}")

    # NOTE the stream=True parameter below
    with requests.get(url, stream=True) as r:
        r.raise_for_status()

        # get the total length of the file and create block size
        length = r.headers.get("Content-Length")
        if length:
            length = int(length)
            blocksize = max(4096, length//100)
        else:
            # ask if there is a better number to assign this
            blocksize = 1000000

        # Write to file in chunks and update the progress bar
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=blocksize): 
                f.write(chunk)
                size += len(chunk)
                if length: print('{:.2f}%'.format((size/length)*100), end='\r')

        # Log the file that has been downloaded
        DLDICT.update({md5hash: file_name})
        if VERBOSE: print("done")


    return local_filename

def download_and_verify(hash, file_name):
    """ download and verify the files"""
    file_path = PATH_DIR + file_name
    url = BASE_URL + "/" + file_name

    try:
        # Download the file 
        download_file(url, file_name, hash)

        # Perform md5sum check if file exists.
        if not pathlib.Path(file_path).exists(): 
            ERRDICT.update({file_name: {"Error": "Download failed. file not found in folder"}})
        else:
            # perform md5sum check on the the hash
            md5sumCheck(hash, file_path)

    except KeyboardInterrupt:
        ERRDICT.update({file_name: {"Error": "User Interrupted process."}})
    except:
        ERRDICT.update({file_name: {"Error": "Download failed. Connection error"}})

    

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
        with open("./pub/"+SUM_FILE, "w") as file: file.write(html)
    
    # Check if the file exists in the created folder
    if not os.path.exists(f"{PATH_DIR}/sum"): 
        if VERBOSE: print("Error: Failed to download the 'sum' file.")
        return 1
    else: 
        if VERBOSE: print("Succesfully downloaded")
        return 0


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
                EXISDICT.update({split[1] : "Already exists. No Corruption"})
    
    # TODO Only include the the filenames that have json unicode in them
    for hash, filename in hashAndFile.copy().items(): 
        if "json_ascii" not in filename: del hashAndFile[hash]

    # NOTE Remove after checking
    if VERBOSE:
        for hash, filename in hashAndFile.copy().items(): print(hash,":", filename)

    # Download the files based on the key value pair
    for hash, filename in hashAndFile.items(): download_and_verify(hash, filename)


def main():

    try:
        # first download the sum file
        download_sum_file()

        # Check what has been downloaded and perform and md5sumcheck

        # Then parse the sum file and download
        parse_sum_file_and_download()

        # Log the downloaded, existin, and corrupted files. 
        logger()

    except KeyboardInterrupt:
        ERRDICT.update({"Error": "User Interrupted process."})

    except ConnectionError:
        ERRDICT.update({"Error": "Connection was lost."})
  

main()  
logger()
