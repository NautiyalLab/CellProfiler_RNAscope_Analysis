# MISCELLANEOUS PACKAGE IMPORT BLOCK

import os  # For file I/O processes
# Enable GUI selection of some file I/O components
import tkinter.filedialog
import glob  # Read in image files from subdirectories
import pandas as pd  # Create and save output file
import numpy as np

# CELLPROFILER IMPORT BLOCK

# See: https://github.com/CellProfiler/CellProfiler/wiki/CellProfiler-as-a-Python-package
import cellprofiler_core.pipeline
import cellprofiler_core.preferences
import cellprofiler_core.utilities.java
import pathlib

cellprofiler_core.preferences.set_headless()

# Start the Java VM
cellprofiler_core.utilities.java.start_java()

# USER INPUT BLOCK

# N.B. Set any variable, except savefile_name or image_ext, to '' to use GUI for that input.

# Set path to pipeline file here
cp_pipe_file = "multiplex RNAscope quantification_Erben17_SSD.cppipe"
# Run one sample image from your dataset using the GUI prior to batch processing
#     to ensure module parameters are correct
# Batch processing in this file is written for the output of
#     "multiplex RNAscope quantification_Erben17_SSD.cppipe"

# Set Experiment's parent directory here
parent_dir = ''
# The organization and naming conventions of images within your folders should match
#     what is expected by your chosen .cppipe file.
# This script assumes that the experiment is organized such that individual channels for each
#    image are kept in named subdirectories within a parent directory.

# Specify image extension
im_file_ext = '.tif'

# Output Directory
out_dir = ''
savefile_name = 'CellProfiler_BatchProcessing_Output.csv'

# LOAD PIPELINE

pipeline = cellprofiler_core.pipeline.Pipeline()
if cp_pipe_file == '':
    root = tkinter.Tk()
    root.withdraw()
    home = os.path.expanduser('~')
    print('Select CellProfiler Pipeline (.cppipe) File')
    parent_dir = tkinter.filedialog.askdirectory(initialdir=home)  # ask_directory

pipeline.load(cp_pipe_file)

# DISPLAY PIPELINE MODULES AND DISABLE DEFAULT FILE-SAVE

# Display all module settings
export_to_spreadsheet_number = -1
for module in pipeline.modules():
    print(module.to_dict()['module_num'] - 1, module.to_dict()['module_name'])

    # and get the location of ExportToSpreadsheet if it exists
    if module.to_dict()['module_name'] == 'ExportToSpreadsheet':
        export_to_spreadsheet_number = module.to_dict()['module_num'] - 1

# Disable ExportToSpreadsheet
if export_to_spreadsheet_number >= 0:
    pipeline.disable_module(pipeline.modules()[export_to_spreadsheet_number])
    # Set export_to_spreadsheet back to -1 so that another module can't be deleted.
    export_to_spreadsheet_number = -1

# FIND IMAGE DIRECTORIES IN PARENT

if parent_dir == '':
    root = tkinter.Tk()
    root.withdraw()
    home = os.path.expanduser('~')
    parent_dir = tkinter.filedialog.askdirectory(initialdir=home)  # ask_directory

# Get contents of parent directory
image_directories = glob.glob(os.path.join(parent_dir, '*'))

# Filter out non-directories (i.e. filter out regular files)
image_directories = list(filter(os.path.isdir, image_directories))
print("Preparing to analyze images from \n", image_directories)

# MAIN EXECUTION LOOP

# Create output dataframe:
cell_counts = pd.DataFrame(index=range(len(image_directories)), columns=['ImageName', 'TotalCells',
                                                                         'G', 'R', 'W',
                                                                         'GR', 'GW', 'RW', 'GRW'])
cell_counts.loc[:, :] = 0

# Used in categorizing and counting cells
category_code_dict = {
    'G': 4,
    'R': 2,
    'W': 1,
    'GR': 6,
    'GW': 5,
    'RW': 3,
    'GRW': 7
}

for im_num, input_dir in enumerate(image_directories):

    # Read in Files
    file_list = list(pathlib.Path(input_dir).absolute().glob(f'*{im_file_ext}'))
    print(file_list)
    files = [file.as_uri() for file in file_list]
    pipeline.read_file_list(files)

    # Run pipeline
    output_measurements = pipeline.run()

    # Read out image name and total cells into DataFrame
    cell_counts.loc[im_num, 'TotalCells'] = output_measurements.get_measurement('Cells', 'Parent_Nuclei').size
    cell_counts.loc[im_num, 'ImageName'] = os.path.basename(input_dir)

    # Categorize and count cells.
    category_codes = (output_measurements.get_measurement('Cells', 'Children_GreenCells_Count') * 4) + \
                     (output_measurements.get_measurement('Cells', 'Children_RedCells_Count') * 2) + \
                     output_measurements.get_measurement('Cells', 'Children_WhiteCells_Count')

    for category, code in category_code_dict.items():
        cell_counts.loc[im_num, category] = np.sum(category_codes == code)

# SAVE OUTPUT TO FILE

if out_dir == '':
    root = tkinter.Tk()
    root.withdraw()
    home = os.path.expanduser('~')
    out_dir = tkinter.filedialog.askdirectory(initialdir=home)  # ask_directory

#   If the directory doesn't exist, create it
if not os.path.isdir(out_dir):
    os.mkdir(out_dir)

save_path = os.path.join(out_dir, savefile_name)
cell_counts.to_csv(save_path)

# Shut down Java VM before closing
cellprofiler_core.utilities.java.stop_java()
