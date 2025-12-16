import download as dl
import build_db as bdb
import sys
from gooey import Gooey, GooeyParser

# downloadable files
downloadables = ["all xml_ascii.tar.gz", "all xml_unicode.tar.gz", "all json_ascii.tar.gz", "all json_unicode.tar.gz",
                 "README.txt", "pmc.key", "pmc_ascii.key", "pubmed.key", "sum"]
downloadables += [file for file in dl.getsum().values()]

about = {
    'type': 'Link',
    'menuTitle': 'About Us',
    'url': 'https://www.liverpool.ac.uk/computational-biology-facility/'
}

@Gooey(program_name="PMC Database and Downloader Tools", image_dir='./src/img',
tabbed_groups=True,
show_sidebar=True,
menu=[{'name':'File', 'items':[about]}, 
      {'name':'Help', 'items':[]}
     ]
)
def gui():
    # gui for download.py
    parser = GooeyParser(
    prog='downloader',
    description = """Tools for https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC. For list of available files.\nUse the aforementioned link or type ls. Functionalities of the tools are listed in the options below.
                  """
    )
    
    # widgets for downloading files
    group1 = parser.add_argument_group('Download settings')
    group1.add_argument('-s', metavar="Save", type=str, help="Folder where your file the file should be saved", widget="DirChooser")
    group1.add_argument('-d', metavar="Download", type=str, nargs=1, help="download a file from the link. To bulk download scroll to the bottom most of the choices.", widget="FilterableDropdown", choices=downloadables)
    
    # widgets for storing in database
    group2 = parser.add_argument_group('Database settings')
    group2.add_argument('-i', metavar="Insert", action="store_true", help="Insert the downloaded files into the database?", widget="BlockCheckbox")
    group2.add_argument('-b', metavar="Database", type=str, nargs=1, help="Choose the database file (ex. pmc.db). If none is chosen then system will build the database on the chosen folder", widget="FileChooser")
    
    args = parser.parse_args()
    
    # donwload handler
    if args.d[0] in ["all xml_ascii.tar.gz", "all xml_unicode.tar.gz", "all json_ascii.tar.gz", "all json_unicode.tar.gz"]:
        try:
            print(f"\nChecking existing PMC files in {args.s}")
            if dl.checkExistence("update") or dl.checkExistence("sum-new"):
                md5mode = False
            else:
                md5mode = True
            dl.bulkdownload(path=args.s, filetype="json_ascii", md5mode=md5mode)
        except KeyboardInterrupt:
            # Exit the Program when keyboard interrupt is pressed and log.
            sys.exit(1)
    else:
        # check if the file is corrupted first using th
        dl.download(args.d[0], args.s)
        
    # database handler
    if args.i: # if insert into db was chosen
        files = [f"{dl.log["Path"]}/{x}" for x in dl.log["Downloads"].keys()]
        conn, conn_kw, cur, cur_kw = connectDb(args.b)
        print("Beginning Bulk processing of tar files for the database")
        tar_file_paths = processPaths(files)
        processTar(tar_file_paths, conn, cur, conn_kw, cur_kw)
        print("done bulk processing tarfile")
        

if __name__ == "__main__":
    gui()