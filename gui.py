import download as dl
import sys
from gooey import Gooey, GooeyParser


@Gooey(program_name="PMC Database and Downloader Tools")
def gui():
    # gui for download.py

    # downloadable files
    downloadables = ["all xml_ascii.tar.gz", "all xml_unicode.tar.gz", "all json_ascii.tar.gz", "all json_unicode.tar.gz",
                     "README.txt", "pmc.key", "pmc_ascii.key", "pubmed.key", "sum"]
    downloadables += [file for file in dl.getsum().values()]
     
     
    parser = GooeyParser(
    prog='python download.py',
    description = """Tools for https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC. For list of available files.\nUse the aforementioned link or type ls. Functionalities of the tools are listed in the options below.
                  """
    )
    
    # widgets for downloading files
    group1 = parser.add_argument_group('Downloads')
    group1.add_argument('-s', metavar="Save", help="Folder where your file the file should be saved", widget="DirChooser")
    group1.add_argument('-m', metavar="File Integrity Checker", type=str, nargs=1, help="Check if file exists. Then, verify file integrity using md5hash.", widget="FileChooser")
    group1.add_argument('-d', metavar="Download", type=str, nargs=1, help="download a file from the link. To bulk download scroll to the bottom most of the choices.", widget="FilterableDropdown", choices=downloadables)
    
    # widgets for storing in database
    group2 = parser.add_argument_group('Database')
    group2.add_argument('-i', metavar="Insert", help="Choose files to insert inside the database", widget="MultiFileChooser")
    group2.add_argument('-b', metavar="Database", type=str, nargs=1, help="Choose the database file. If none is chosen then system will build the database", widget="FileChooser")
    
    args = parser.parse_args()
    
    # if len(sys.argv) == 1:
        # parser.print_help()
        # sys.exit(1)
    
    # arguments from downloads
    print(args.s)
    print(args.d[0])
    print(args.m)
    
    # donwload handler
    if args.d[0] in ["all xml_ascii.tar.gz", "all xml_unicode.tar.gz", "all json_ascii.tar.gz", "all json_unicode.tar.gz"]:
        try:
            print(f"\nChecking existing PMC files in {args.b[0]}")
            if dl.checkExistence("update") or dl.checkExistence("sum-new"):
                md5mode = False
            else:
                md5mode = True
            dl.bulkdownload(path=args.b[0], filetype="json_ascii", md5mode=md5mode)
        except KeyboardInterrupt:
            # Exit the Program when keyboard interrupt is pressed and log.
            sys.exit(1)
    else:
        # check if the file is corrupted first using th
        dl.download(args.d[0], args.s)

if __name__ == "__main__":
    gui()