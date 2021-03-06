#!/usr/bin/env python3
# This script converts boundingBox coordinates from ASF vertex to topsStack format
# Author: Falk Amelung
# Created:5/2019
#######################################

import sys
import os
import argparse
from minsar.objects import message_rsmas

inps = None


EXAMPLE = """example:
  convert_boundingbox.py 103.2,30.95,103.85,30.95,103.85,31.54,103.2,31.54,103.2,30.95
  convert_boundingbox.py " -72.71,-41.47,-72.46,-41.47,-72.46,-41.25,-72.71,-41.25,-72.71,-41.47"
  convert_boundingbox.py '39.46 39.82 118.2 118.9'
"""


def create_parser():
    """ Creates command line argument parser object. """

    parser = argparse.ArgumentParser()
    parser = argparse.ArgumentParser(description='Utility to convert boundingBox formats.',
                                     formatter_class=argparse.RawTextHelpFormatter,
                                     epilog=EXAMPLE)
    parser.add_argument('boundingBox', nargs='?', help='coordinates of bounding box to convert')

    return parser


def command_line_parse(args):
    """ Parses command line agurments into inps variable. """
    parser = create_parser()
    return parser.parse_args(args)


def run_convert_boundingbox(input):
    """ converts
    ASF Vertex boundingBox:
    103.2,30.95,103.85,30.95,103.85,31.54,103.2,31.54,103.2,30.95  
    103.2,   30.95,   103.85,  30.95,   103.85,  31.54,   103.2,   31.54,   103.2,   30.95  
    min_lon, min_lat, max_lon, min_lat, max_lon, max_lat, min_lon, max_lat, min_lon, min_lat

    topsStack boundingBox (bbox):
    39.46   39.82   118.2   118.9
    min_lat max_lat min_lon max_lon
    """

    # Compute SSARA options to use

    if ',' in input[0]:
        toks=input[0].split(',')
    else:
        toks=input[0].split(' ')

    if len(toks) == 10:     # ASF Vertex
        min_lon = toks[0].strip()
        min_lat = toks[1].strip()
        max_lon = toks[2].strip()
        max_lat = toks[5].strip()
    elif len(toks) == 4:    # topsStack boundingBox 
        min_lat = toks[0].strip()
        max_lat = toks[1].strip()
        min_lon = toks[2].strip()
        max_lon = toks[3].strip()

    out_asf = min_lon + ',' + min_lat + ',' + max_lon + ',' + min_lat + ',' + max_lon + ',' + max_lat + ',' + min_lon + ',' + max_lat + ',' + min_lon + ',' + min_lat
    out_sentinel_stack = min_lat +' '+ max_lat +' '+ min_lon +' '+ max_lon 
    
    print('\n'+'ASF Vertex and topsStack formats:'+'\n')
    print(out_asf)
    print(out_sentinel_stack)

    return 

###########################################################################################


if __name__ == '__main__':
    message_rsmas.log('.', os.path.basename(__file__) + ' ' + ' '.join(sys.argv[1::]))
    inps = command_line_parse(sys.argv[1:])
    run_convert_boundingbox(sys.argv[1:])

