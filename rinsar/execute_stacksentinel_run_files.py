#!/usr/bin/env python3
########################
# Author: Sara Mirzaee
#######################

import os
import sys
import glob
from rinsar.rsmas_logging import loglevel
import argparse
import subprocess
from rinsar import messageRsmas
from rinsar._process_utilities import get_project_name, send_logger
from rinsar._process_utilities import remove_zero_size_or_length_error_files, concatenate_error_files 
from rinsar._process_utilities import move_error_files_except_first, move_stdout_files
from rinsar._processSteps import create_or_update_template
from rinsar._process_utilities import remove_zero_size_or_length_error_files, raise_exception_if_job_exited
import rinsar.create_batch as cb

logger_exec_run  = send_logger()

##############################################################################
EXAMPLE = """example:
  execute_stacksentinel_run_files.py LombokSenAT156VV.template 
"""

def main(args=None):

    command = os.path.basename(__file__) + ' ' + ' '.join(args[0:])
    messageRsmas.log(command)

    inps = command_line_parse(sys.argv[1:])

    #########################################
    # Submit job
    #########################################
    if inps.submit_flag:
        job_file_name = 'execute_stacksentinel_run_files'
        work_dir = os.getcwd()
        job_name = inps.custom_template_file.split(os.sep)[-1].split('.')[0]

        cb.submit_script(job_name, job_file_name, sys.argv[:], work_dir, inps.wall_time)
        sys.exit(0);

    inps.project_name = get_project_name(inps.custom_template_file)
    inps.work_dir = os.getenv('SCRATCHDIR') + '/' + inps.project_name
    inps = create_or_update_template(inps)
    run_file_list = get_run_files(inps)

    if inps.stop_run == 999:
        inps.stop_run = len(run_file_list)

    logger_exec_run.log(loglevel.INFO, "Executing Runfiles {} to {}".format(inps.start_run,inps.stop_run))

    memoryuse = set_memory_defaults()

    submit_isce_jobs(run_file_list[inps.start_run - 1:inps.stop_run], inps.work_dir, memoryuse)
    
    remove_zero_size_or_length_error_files(directory='run_files')
    concatenate_error_files(directory='run_files',out_name='out_stack_sentinel_errorfiles.e')
    move_error_files_except_first(directory='run_files')
    move_stdout_files(directory='run_files')

    logger_exec_run.log(loglevel.INFO, "-----------------Done Executing Run files-------------------")
    
    
def create_parser():
    """ Creates command line argument parser object. """

    #parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, epilog=EXAMPLE)
    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--version', action='version', version='%(prog)s 0.1')
    parser.add_argument('custom_template_file', nargs='?',
                        help='custom template with option settings.\n')
    parser.add_argument( '--submit', dest='submit_flag', action='store_true', help='submits job')
    parser.add_argument('--startrun', dest='start_run', default='1', type=int,
                        help='run_file number to start with, default=1')
    parser.add_argument('--stoprun', dest='stop_run', default='999', type=int,
                        help='run_file number to start with, default: last file')
    parser.add_argument( '--walltime', dest='wall_time', type=str, default='10:00',
                        help='walltime, e.g. 2:00 (default: 10:00)')

    return parser


def command_line_parse(args):
    """ Parses command line agurments into inps variable. """

    parser = create_parser()
    inps = parser.parse_args(args)

    return inps


def get_run_files(inps):
    """ Reads stackSentinel runfiles to a list. """

    runfiles = os.path.join(inps.work_dir, 'run_files_list')
    run_file_list = []
    with open(runfiles, 'r') as f:
        new_f = f.readlines()
        for line in new_f:
            run_file_list.append('run_files/'+line.split('/')[-1][:-1])

    return run_file_list


def set_memory_defaults():
    """ Sets an optimized memory value for each job. """

    memoryuse = {'unpack_slc_topo_master':'3700',
                 'average_baseline':'3700',
                 'extract_burst_overlaps':'3700',
                 'overlap_geo2rdr_resample':'4000',
                 'pairs_misreg':'3700',
                 'timeseries_misreg':'3700',
                 'geo2rdr_resample':'5000',
                 'extract_stack_valid_region':'3700',
                 'merge':'3700',
                 'merge_burst_igram': '3700',
                 'grid_baseline':'3700',
                 'generate_igram':'3700',
                 'filter_coherence':'6000',
                 'merge_master_slave_slc':'3700',
                 'unwrap':'3700'}

    return memoryuse


def submit_isce_jobs(run_file_list, cwd, memoryuse):
    """ Submits stackSentinel runfile jobs. """

    for item in run_file_list:
        item_memory = '_'
        item_memory = item_memory.join(item.split('_')[3::])
        try:
            memorymax = str(memoryuse[item_memory])
        except:
            memorymax = '3700'

        if os.getenv('QUEUENAME') == 'debug':
            walltimelimit = '0:30'
        else:
            walltimelimit = '4:00'

            vlong, long, short = '3:00', '1:00', '0:30'
            vlong, long, short = '6:00', '2:00', '1:00'
            vlong, long, short = '9:00', '3:00', '2:00'
            vlong, long, short = '12:00', '4:00', '2:00'

            item_name = os.path.basename(item)

            if item_name == 'run_1_unpack_slc_topo_master':
                walltimelimit = vlong 
            if item_name == 'run_2_average_baseline':
                walltimelimit = short
            if item_name == 'run_3_extract_burst_overlaps':
                walltimelimit = short
            if item_name == 'run_4_overlap_geo2rdr_resample':
                walltimelimit = long
            if item_name == 'run_5_pairs_misreg':
                walltimelimit = short
            if item_name == 'run_6_timeseries_misreg':
                walltimelimit = short
            if item_name == 'run_7_geo2rdr_resample':
                walltimelimit = vlong
            if item_name == 'run_8_extract_stack_valid_region':
                walltimelimit = short
            if item_name == 'run_9_merge_burst_igram':
                walltimelimit = long
            if item_name == 'run_10_filter_coherence':
                walltimelimit = short
            if item_name == 'run_11_merge_master_slave_slc':
                walltimelimit = short
            if item_name == 'run_12_unwrap':
                walltimelimit = short

        if item_memory == 'phase_linking':
            walltimelimit = '40:00'

        queuename = os.getenv('QUEUENAME')

        #cmd = 'createBatch.pl ' + cwd + '/' + item + ' memory=' + memorymax + ' walltime=' + walltimelimit + ' QUEUENAME=' + queuename
        #cmd = 'create_batch.py ' + cwd + '/' + item

        cmd = 'create_batch.py ' + cwd + '/' + item + ' --memory=' + memorymax + ' --walltime=' + walltimelimit + ' --queuename ' + queuename
        print('command:',cmd)
        status = subprocess.Popen(cmd, shell=True).wait()
        if status is not 0:
            logger_exec_run.log(loglevel.ERROR, 'ERROR submitting {} using create_batch.py'.format(item))
            raise Exception('ERROR submitting {} using createBatch.pl'.format(item))
            
        job_folder = cwd + '/' + item + '_out_jobs'
        print('jobfolder:',job_folder)
        
        remove_zero_size_or_length_error_files(directory='run_files')
        raise_exception_if_job_exited(directory='run_files')

        #if not os.path.isdir(job_folder):
        #    os.makedirs(job_folder)
        #mvlist = ['*.e ', '*.o ', '*.job ']
        #for mvitem in mvlist:
        #    cmd = 'mv ' + cwd + '/run_files/' + mvitem + job_folder
        #    print('move command:',cmd)
        #    os.system(cmd) 

    return None

##############################################################################

if __name__ == "__main__":
    main(sys.argv[1:])

