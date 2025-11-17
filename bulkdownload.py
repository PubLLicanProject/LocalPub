import urllib.request
import requests
import hashlib
import pathlib
import gc
import os

BASE_URL="https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
SUM_FILE="sum"
PATH_DIR = "./pub"

# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def md5sumCheck(original_md5, file_to_check):
    # Source - https://stackoverflow.com/a
    # Posted by PSS, modified by community. See post 'Timeline' for change history
    # Retrieved 2025-11-14, License - CC BY-SA 4.0

    # Import hashlib library (md5 method is part of it)
    import hashlib

    # Open,close, read file and calculate MD5 on its contents 
    with open(file_to_check, 'rb') as file:
        # read contents of the file
        data = file.read()    
        # pipe contents of the file through
        md5_returned = hashlib.md5(data).hexdigest()

    # Finally compare original MD5 with freshly calculated
    if original_md5 == md5_returned:
        print("MD5 verified.")
        return 1
    else:
        print("MD5 verification failed!.")
        return 0

def resume():
    # TODO find the folder where the compressed files are found

    # TODO Need to do md5sum check to see file integrity
    # md5sumCheck(original_md5, file_to_check)

    # TODO for corrupted files or incomplete file 

    return




def download_file(url, file_name, md5hash):

    size = 0

    # print the current file being downloaded
    print(f"{md5hash} {file_name}")

    local_filename = PATH_DIR +"/"+ url.split('/')[-1]
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
            print("done")


    return local_filename



# ------------------------------------------------------------------------------------------------------------------------------------------------------------------

def download_and_verify(hash, file_name):
    """ download and verify the files"""
    file_path = "./" + file_name
    url = BASE_URL + "/" + file_name

    download_file(url, file_name, hash)

    # TODO test if the file exists, if it doesnt then print failed to download
    # if pathlib.Path(file_path).exists(): print("The file exists.")
    # OR do a try except then if file fails to download then print download failed

    # TODO perform md5sum check on the the hash
    # md5sumCheck(original_md5, file_to_check)

    # param1: expected_hash, param2: filename
    # local expected_hash=$1
    # local filename=$2
    # local file_url="$BASE_URL/$filename"

    # echo "Downloading $filename..."

    # # download file from file_url and name as filename
    # wget -nv -O "$filename" "$file_url"

    # # test if the file exists
    # if [ ! -f "$filename" ]; then
    #     echo "**Error** : Failed to download $filename."
    # fi



def download_sum_file():
    # download file using BASE_URL
    print("Downloading the sum file...")

    # Create the folder where the the sum file would be stored
    directory = pathlib.Path(PATH_DIR)
    directory.mkdir(parents=True, exist_ok=True)

    # read the file from the URL
    with urllib.request.urlopen(BASE_URL + "/" + SUM_FILE) as f:
        html = f.read().decode('utf-8')
        # save the file into the folder as 'sum'
        with open("./pub/"+SUM_FILE, "w") as file: file.write(html)
    
    # Check if the file exists in the created folder
    if not os.path.exists(f"{PATH_DIR}/sum"): 
        print("Error: Failed to download the 'sum' file.")
        return 0
    else: 
        print("Succesfully downloaded")
        return 1


# Function to parse the sum file and download json_unicode files
def parse_sum_file_and_download():
    """ Parse the sum file and download the files inside it"""

    hashAndFile = {}
    with open(PATH_DIR + f"/{SUM_FILE}", "r") as f:
        for line in f: 
            split = line.split()
            hashAndFile.update({split[0] : split[1]})

    # Only include the the filenames that have json unicode in them
    for hash, filename in hashAndFile.copy().items(): 
        if "json_unicode" not in filename: del hashAndFile[hash]

    # Download the files based on the key value pair
    for hash, filename in hashAndFile.items(): download_and_verify(hash, filename)


def main():
    # first download the sum file
    # download_sum_file()
    # Then parse the sum file and download
    # parse_sum_file_and_download()
    print("Done")

main()  

