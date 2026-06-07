import argparse
import sys
import build_db as dbd
from gooey import Gooey, GooeyParser
from pathlib import Path
import sqlite3


def query(cur, args):
    # Build the query string
    qstr = ""
    if args.c != None:
        qstr += """SELECT {0}""".format(args.c[0])
    if args.t != None:
        qstr += """ FROM {0}""".format(args.t[0])
    if args.w != None:
        qstr += """ WHERE {0}""".format(args.w[0])
    if args.g != None:
        qstr +=""" GROUP BY {0}""".format(args.g[0])
    if args.hv != None:
        qstr +=""" HAVING {0}""".format(args.hv[0])
    if args.o != None:
       qstr += """ ORDER BY {0}""".format(args.o[0])
    qstr += ";"

    return cur.execute(qstr)


@Gooey(program_name='PMC Database Query', image_dir='./src/img')
def main():
    parser = GooeyParser(
    prog='python queryGui.py',
    description = """Tools to query the database  https://ftp.ncbi.nlm.nih.gov/pub/wilbur/BioC-PMC. The query uses SQL for data manipulation. Note: inside pmc.db is a table called 'records' and inside pmc_kw is a database called 'keywords'. The records table have columns (attributes): id, pmid, and content. The 'keyword' table has columns (attributes) keyword, pmid, and type.
                  """
    )
    
    # widgets for downloading files
    group1 = parser.add_argument_group('Query')
    group1.add_argument('-d', metavar="Database", help="Folder where your file the file should be saved", widget="FileChooser")
    group1.add_argument('-t', metavar="(FROM) Table", type=str, nargs=1, help="Select a table from the database", widget="FilterableDropdown", choices=['records', 'keywords'])
    group1.add_argument('-c', metavar="(SELECT) Columns", type=str, nargs=1, help="Select the columns to be displayed", widget="FilterableDropdown", choices=['id','pmid', 'keyword', 'type'])
    group1.add_argument('-w', metavar="(WHERE) Condition", type=str, nargs=1, help="SQL WHERE condition", action="store")
    group1.add_argument('-g', metavar="(GROUP BY) column_name(s)", type=str, nargs=1, help="group output by column name", action="store")
    group1.add_argument('-hv',metavar="(HAVING) Condition", type=str, nargs=1, help="group column name having a condition", action="store")
    group1.add_argument('-o', metavar="(ORDER BY) column_name(s)", type=str, nargs=1, help="order the results based on a column name", action="store")
    args = parser.parse_args()
    
    #connect to database
    conn = sqlite3.connect(str(Path(args.d).resolve()))
    cur = conn.cursor()
    res = query(cur, args)
    print(res.fetchall())

if __name__== "__main__":
    main()