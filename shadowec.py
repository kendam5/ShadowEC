# MODULE NAME: shadowec.py
# Description of MODULE:
# This is the main processing script for ShadowEC. This script creates objects detailing each Shadow Copy on
# a system. Using this class in combination with the os modules walk and stat allows for the collection of metadata
# for each of the files located in each of Shadow Copies. The metadata of the files hashed using MD5 and stored
# in CSV files for further processing and analysis. This script allows for simple comparison based on created and
# modified times of files.
# ------------------------------------------------------------------------------------------------------------------
# Author: Kenneth Damlien
# Email: kennethdamlien@live.no
# ------------------------------------------------------------------------------------------------------------------
# IMPORTS GOES HERE:
import re, sys, time, os, glob, platform, ctypes, hashlib, csv, calendar, time, ErrorLog
from datetime import datetime
from subprocess import call, Popen, PIPE, STDOUT
from optparse import OptionParser
# ------------------------------------------------------------------------------------------------------------------
# GLOBAL VARIABLES GOES HERE:
WINDOWS_DIR = "\\"
target = "Users" + WINDOWS_DIR
# ------------------------------------------------------------------------------------------------------------------
# COMMAND LINE OPTIONS:
parser = OptionParser(usage="Shadowec.py <option>")
parser.add_option("-l", "--list", action= "store_true", help= "List every Volume Shadow Copy on Current Volume")
parser.add_option("-p", "--parse", action= "store_true", help= "Process All Shadow Copies or Compare Shadow Copies")
parser.add_option("-v", "--visualize", action= "store_true", help= "Visualize processed data")
parser.add_option("-e", "--exit", action= "store_true", help= "Exit the command line tool")
(options, args) = parser.parse_args()
# ------------------------------------------------------------------------------------------------------------------
# Class Shadow, function shadowparse() and list_volumes() are heavily inspired by
# Brian Madden's ShadowVolume2.py script, and is located below:
class Shadow:
    # Class describing each Shadow Copy
    def __init__(self, attributes):
        self.attributes = attributes
    def machine(self):
        return self.attributes["Originating Machine"]
    def creationtime(self):
        return self.attributes["creation time"]
    def path(self):
        return self.attributes["Shadow Copy Volume"]
    def vname(self):
        return self.path().split("\\")[-1]

def shadowparse(vssadmin):
    # Parse the list from list_volumes() and create objects of Class Shadow

    return_object = []
    current_copy = None
    x = vssadmin.strip().splitlines()

    for line in x:
        line = line.strip()
        if line =="":
            if current_copy:
                return_object.append(Shadow(current_copy))
                current_copy = None
            continue

        if line.startswith("Contents"):
            current_copy = {}
            vid = line.split(":")[1][1:]
            current_copy["ID"] = vid
            continue
        if not current_copy:
            continue

        colon = line.find(":")
        if colon >=0:
            name = line [0:colon]
            value = line[colon+2:]
            if name.endswith("creation time"): name="creation time"
            current_copy[name] = value
    return return_object

def list_volumes():
    # Get Shadow Copy details from vssadmin.exe and store in list
    vss_list = Popen(["vssadmin.exe", "list", "shadows"], stdout=PIPE).communicate()[0]
    vss_list = vss_list.decode("utf-8")
    return shadowparse(vss_list)

# End of Class functions
# ------------------------------------------------------------------------------------------------------------------

def intro():
    # Printed to console when ShadowEC is executed without any options
    print("ShadowEC")
    print("This command line tools walks all user files in every shadow copy on a given volume")
    print("and creates a report file detailing path, filename, and metadata for each file")
    print("Author: Kenneth Damlien")
    print("Email: kennethdamlien@live.no \n")


def epochtime(volumetime):
    # Creates a UNIX timestamp based on the time and date given by the Shadow Copy
    # Create datetime object from string
    in_time = datetime.strptime(volumetime, "%m/%d/%Y %I:%M:%S %p")
    # Reformat the datetime object to reflect format of Shadow Copy files
    out_time = datetime.strftime(in_time, "%d.%m.%Y %H:%M:%S")
    # Convert reformatted human readable time to Unix timestamp
    epoch = int(datetime.strptime(out_time, "%d.%m.%Y %H:%M:%S").timestamp())
    # Return Uinx timestamp
    return epoch

def mactimes(mactime):
    # Converts provided UNIX timestamp to human readable format and returns it
    try:
        year, month, day, hour, minute, second = time.localtime(mactime)[:-3]
        converted = "%02d/%02d/%d %02d:%02d:%02d" % (day, month, year, hour, minute, second)
    except AttributeError as e:
        errormsg = str(e)
        ErrorLog.error(filename="shadowec.mactimes().txt", error=e, errortype="AttributeError")
        print(e)
        # Return a human readable date and time format
    return converted


def get_digest(shadowfile):
    # Opens file as binary and and hash chunks of file, return full MD5 hash
    # define size of chunk in bytes
    BSIZE = 65536
    md5 = hashlib.md5()
    # open file as binary
    with open(shadowfile, "rb") as f:
        while True:
            # read file in chunks
            chunk = f.read(BSIZE)
            if not chunk:
                break
            md5.update(chunk)
    # return md5 hash of the contents of the file
    return md5.hexdigest()

def create_report(reportname):
    directory = "ProcessingOutput"

    filename = reportname + ".csv"
    try:
        with open(os.path.join(directory, filename), "w") as f:
            fields = ["Filename", "Path", "MD5", "Size", "Modified Time", "Access Time", "Created Time"]
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
    except:
        print("Could not create file in directory")

def append_report(file, path, md5, size, mtime, atime, ctime, reportname):
    directory = "ProcessingOutput"
    filename = reportname + ".csv"

    with open(os.path.join(directory, filename), "a", newline="") as f:
        fields = ["Filename", "Path", "MD5", "Size", "Modified Time", "Access Time", "Created Time"]
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writerow({"Filename" : file, "Path" : path, "MD5" : md5, "Size" : size, "Modified Time" : mtime,
                         "Access Time" : atime, "Created Time" : ctime})

def user_select(volumes):
    from collections import defaultdict

    x = 0
    volumenames = defaultdict(dict)

    print("\nSelect your baseline Shadowcopy. ShadowSEC will generate a report on every file contained "
          "in this Shadow Copy, and will generate reports on all files created after the baseline date. \n")

    for v in volumes:
        x += 1
        print("[{}] =".format(x), v.vname(), "Created at: {}".format(v.creationtime()))

        volumenames[x] = v.path()
    return volumenames

def get_volumedate(volumes):
    from collections import defaultdict

    x = 0
    volumedate = defaultdict(dict)

    for v in volumes:
        x += 1
        volumedate[x] = v.creationtime()
    return volumedate

def process_copy(volumes, vpath, reportname, ptype, shadowtime):


    count = 0
    seen = []

    path = vpath # + WINDOWS_DIR + target
    for root, dirs, filename in os.walk(path):
        for file in filename:
            shadowfile = os.path.join(root, file)
            try:
                count += 1
                print("{:s}\r".format(""), "{:s}\r".format(""), end="", flush=True)
                print("Processing file:", count, "in:", vpath.split("\\")[-1], end="")
                # Pass each file through the hashing function
                md5 = get_digest(shadowfile)
                stats = os.stat(shadowfile)
                # Collect metadata for each file:
                # Record file size in KB
                size = stats.st_size / 1024
                # Modified time
                mtime = mactimes(stats.st_mtime)
                # Accessed Time
                atime = mactimes(stats.st_atime)
                # Created Time
                ctime = mactimes(stats.st_ctime)

                if ptype == "1":
                    append_report(file, root, md5, size, mtime, atime, ctime, reportname)
                if ptype == "2":
                    # append to file only if created time or mod time is after shadow copy created time
                    if int(stats.st_ctime) > int(shadowtime):
                        # if shadowfile.endswith(filetype):  # This where a possible filter comes in
                        append_report(file, root, md5, size, mtime, atime, ctime, reportname)
            except WindowsError as error:
                ErrorLog.error(filename="shadowec.process_copy().txt", error=error, errortype="WindowsError")
                continue
            except AttributeError as error2:
                ErrorLog.error(filename="shadowec.process_copy().txt", error=error2, errortype="AttributeError")
                continue

def main():
    volumes = list_volumes()
    directory = "ProcessingOutput"

    if len(sys.argv) == 1:
        intro()
        parser.print_help()
        exit()

    if options.list:
        c = 0
        for v in volumes:
            c += 1
            print("\nShadow Volume Number: ", c)
            print("Volume Name: ", v.vname())
            print("Shadow Copy Created on: ", v.creationtime())
            print("Originating Machine: ", v.machine())
            print("Full Path: ", v.path())

    if options.parse:
        try:
            os.makedirs(directory)
        except OSError as e:
            errormsg = str(e)
            ErrorLog.error(filename="shadowec.main().txt", error=e, errortype="OSError")
            print("Folder Already Exists")

        ptype = input("\n 1. Generate Report on All Files on All Available Shadow Copies \n "
                      "2. Compare Shadow Copy Contents \n")

        if ptype == "1":
            reportname = "All_ShadowCopy_Files"
            create_report(reportname)
            for v in volumes:
                vpath = v.path()
                vname = v.vname()
                process_copy(volumes, vpath, vname, ptype, shadowtime="0")

        if ptype == "2":
            # get baseline Shadow Copy
            baseline = user_select(volumes)

            volumedate = get_volumedate(volumes)
            choice = int(input("\nYour selection [Numerical]: "))

            reportname = "Baseline_{}".format(baseline[choice].split("\\")[-1])
            create_report(reportname)
            process_copy(volumes, baseline[choice], reportname, ptype="1", shadowtime="0")
            get_time = epochtime(volumedate[choice])


            # if key > choice means that there are still Shadow Copies left to process
            for key, value in baseline.items():
                if key > choice:
                    reportname = "Compare_{}".format(baseline[key].split("\\")[-1])
                    create_report(reportname)
                    process_copy(volumes, baseline[key], reportname, ptype, get_time)

    if options.visualize:
        import vis
        # Run the visualisation module from vis.py
        vis.vis()

if __name__ == '__main__':
    main()
