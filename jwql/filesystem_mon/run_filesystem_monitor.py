from monitor_filesystem import filesys_monitor
from monitor_filesystem import plot_system_stats

if __name__ == '__main__':
   #filesystem = '.'
   #outdir = './outtest/'
   inputfile='statsfile.txt'
   filebytype = 'filesbytype.txt'
   filesys_monitor()
   plot_system_stats(inputfile,filebytype)
