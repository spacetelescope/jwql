from monitor_filesystem import filesys_monitor
from monitor_filesystem import plot_system_stats


"""
This module calls the filesystem monitoring and plotting modules.

Authors
-------
    - Misty Cracraft
Use
---
           
    Required arguments (in a config.json file):
    ``filepath`` - The path to the input file needs to be in a 
                config.json file in the utils directory
    "outdir" - The path to the output files needs to be in a 
               config.json file in the utils directory.

    Required arguments for plotting:
    "inputfile" - The name of the file to save all of the system
                  statistics to
    "filebytype" - The name of the file to save stats on fits type 
                   files to

    
Dependencies
------------
    
    The user must have a configuration file named ``config.json``
    placed in the utils directory. The file monitor_filesystem.py
    must also be in the directory.

Notes
-----
    This file runs the scripts that calculate the statistics of the
    filesystem and plots the results. The names for inputfile and
    filesbytype variables must match those in the modules
    filesys_monitor and plot_system_stats.

"""
if __name__ == '__main__':

   inputfile='statsfile.txt'
   filebytype = 'filesbytype.txt'
   filesys_monitor()
   plot_system_stats(inputfile,filebytype)
