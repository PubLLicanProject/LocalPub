#!/bin/bash

BASE_URL="https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC"
SUM_FILE="sum"

download_sum_file() {
    echo "Downloading the sum file..."
    wget -q -O "./sum.txt" "$BASE_URL/$SUM_FILE"

    if [ ! -f "$SUM_FILE" ]; then
        echo "Error: Failed to download the 'sum' file."
        exit 1
    fi
}

download_and_verify() {
    local expected_hash=$1
    local filename=$2
    local file_url="$BASE_URL/$filename"

    echo "Downloading $filename..."

    wget -nv -O "$filename" "$file_url"

    if [ ! -f "$filename" ]; then
        echo "**Error** : Failed to download $filename."
    fi

    local downloaded_hash=$(md5sum "$filename" | awk '{print $1}')

    if [ "$downloaded_hash" == "$expected_hash" ]; then
        echo "Completed $filename"
    else
        echo "**Error** : Hash mismatch for $filename"
    fi
}

# Function to parse the sum file and download json_unicode files
parse_sum_file_and_download() {
    while read -r line; do
        local hash=$(echo "$line" | awk '{print $1}')
        local filename=$(echo "$line" | awk '{print $2}')

        if [[ "$filename" == *"json_unicode"* ]]; then
            download_and_verify "$hash" "$filename"
        fi
    done < "$SUM_FILE"
}

main() {
    download_sum_file
    parse_sum_file_and_download
    echo "Done."
}

main