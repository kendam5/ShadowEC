# MODULE NAME: vis.py
# Description of MODULE:
# vis.py uses "Bokeh" to generate visual plots of the provided data. The raw data is the generated .csv
# file from the main ShadowEC module. Current plot grids consists of:
# 1. Amount of filetypes found in every instance of a shadow Copy
# 2. Timeline displaying created, modified and access time for each file in each processes Shadow Copy.
# ------------------------------------------------------------------------------------------------------------------
# Author: Kenneth Damlien
# Email: kennethdamlien@live.no
# ------------------------------------------------------------------------------------------------------------------
# IMPORTS GOES HERE:
from bokeh.layouts import row, column, gridplot
from bokeh.plotting import figure, save, output_file
from bokeh.transform import factor_cmap, factor_mark
from bokeh.models import ColumnDataSource
import csv, os, re, ErrorLog
from collections import defaultdict
from datetime import datetime
from math import pi
# ------------------------------------------------------------------------------------------------------------------
# GLOBAL VARIABLES GOES HERE:
directory = "ProcessingOutput"
visoutput = directory + "\\" + "Visualisation"
# ------------------------------------------------------------------------------------------------------------------
# FUNCTIONS GOES HERE:

def get_filetypelist():
    # Allow user to define which filetypes are to be included in the analysis and plot
    choice = str(input("Input filetypes to include in plots, seperate by comma. Example [jpg, png, pdf]"))
    choice = choice.rsplit(", ")
    # Create and return a list of filetypes
    return choice

def filterdata(directory, file, rowname):

    d = defaultdict(dict)
    # Open .CSV file
    with open (directory + "\\" + file, mode='r') as csvfile:
        csv_reader = csv.DictReader(csvfile, delimiter=',')
        for row in csv_reader:
            try:
                if rowname == "Filename":
                    # Attempt to split filetype from filename, and save filetype as x
                    x = row[rowname].rsplit(".")[1]
                else:
                    # Attempt to split the date (DD/MM/YYYY from time in accessed, modified, created columns)
                    x = row[rowname].split(" ")[0]
                if x in d:
                    # Check if x in dictionary, if exist: + 1, else = 1
                    d[x] = d[x] + 1
                else:
                    d[x] = 1
            except IndexError as e:
                errormsg = str(e)
                # Call module "ErrorLog" to write error message to file
                ErrorLog.error(filename="vis.filterdata().txt", error=errormsg, errortype="IndexError")
                continue
        return d

def createplot(data, filelist, shadowcopy):

    # provided list of files used as factors for x_range
    factors = filelist
    y = []
    # y is a list of the number of filetypes found in provided data
    for x in filelist:
        if x in data:
             y.append(data[x])
        else:
             y.append(x)

    # Create Bokeh Figure, x range swapped out with list of filetypes [factors]
    p = figure(title = shadowcopy, x_axis_label='File Types', y_axis_label='Number of Files', x_range=factors)
    # Create Bokeh bar plot
    p.vbar(x=factors, legend_label="Amount of filetypes found in each shadowcopy", width=0.5,
        bottom=0, top=y, color="blue")
    return p

def createdateplot(created, access, modified, shadowcopy):

    y1 = []
    y2 = []
    y3 = []

    factors = []
    # Add every date found in MAC-times to list of factors (x_range)
    for x in created and access and modified:
        if x in factors:
            continue
        else:
            factors.append(x)
    # Create datetime objects for each item in factor list, sort datetime objectives from earliest to latest (lambda)
    factors.sort(key=lambda date: datetime.strptime(date, '%d/%m/%Y'))

    # Create lists containing datapoints to be plotted to factors
    y1 = appendtolist(factors, created)
    y2 = appendtolist(factors, access)
    y3 = appendtolist(factors, modified)
    # Create Figure
    p = figure(title=shadowcopy, x_axis_label='Dates', y_axis_label='Number of entries', x_range=factors)
    # Create Plot Lines, x_range = factors(dates)
    p.line(x=factors, y=y1, legend_label="Created Files", line_color="blue", line_width=2)
    p.line(x=factors, y=y2, legend_label="Accessed Files", line_color="red", line_width=2)
    p.line(x=factors, y=y3, legend_label="Modified Files", line_color="green", line_width=2)

    p.xaxis.major_label_orientation = pi/4

    return p

def appendtolist(factors, dates):
    list = []
    for x in factors:
        if x in dates:
            list.append(dates[x])
    # ColumnSource data columns needs to be equal. Check for y lenght and add NaN until equal to factors
    while len(list) < len(factors):
        list.append("nan")
        if len(list) == len(factors):
            break
    return list


def createplotgrid(plot, filename):
    # Define location and name of output file
    output_file(visoutput + "\\" + filename + ".html")
    # Specify number of columns in plotgrid:
    grid = gridplot(plot, ncols=2)
    save(grid)

def vis():

    try:
        os.makedirs(visoutput)
    except OSError as e:
        errormsg = str(e)
        ErrorLog.error(filename="vis.vis().txt", error=e, errortype="OSError")
        pass

    s1 = []
    s2 = []

    filelist = os.listdir(directory)
    filetypelist = get_filetypelist()

    for file in filelist:
        if file.endswith(".csv"):
        # if file.startswith("Compare_"):

            shadowcopy = file.rsplit("_")[-1]
            filetypes = filterdata(directory, file, rowname="Filename")
            s1.append(createplot(filetypes, filetypelist, shadowcopy))

            created = filterdata(directory, file, rowname="Created Time")
            modified = filterdata(directory, file, rowname="Modified Time")
            accessed = filterdata(directory, file, rowname="Access Time")
            s2.append(createdateplot(created, accessed, modified, shadowcopy))




    createplotgrid(s1, filename="Filetypes")
    createplotgrid(s2, filename="MAC-Times")