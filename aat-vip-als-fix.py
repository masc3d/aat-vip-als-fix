__author__ = 'masc'
__version__ = '0.1'

_APP_NAME = 'aat-vip-als-fix'

import codecs
import os
import sys
import logging
import gzip

import xml.etree.ElementTree as ET

from collections import namedtuple
from logging import StreamHandler
from argparse import ArgumentParser

# Initialize logging
log = logging.getLogger('')
log.addHandler(StreamHandler(sys.stdout))
log.setLevel(logging.INFO)

# Parse command line
parser = ArgumentParser(prog=_APP_NAME)
parser.add_argument('input_als',
                    type=str,
                    metavar='input-als',
                    help='Converted AAT ALS filename')

parser.add_argument('output_als',
                    type=str,
                    metavar='output-als',
                    help='Output ALS filename')

args = parser.parse_args()

input_als = os.path.abspath(args.input_als)
input_als_dir = os.path.abspath(os.path.join(input_als, (os.pardir)))
output_als = os.path.abspath(args.output_als)

# Dictionary mapping hdp names to relative paths
hdp_dict = dict()

log.info('Converting %s -> %s' % (input_als, output_als))
log.info('Extracting smaple filenames from HDPs')
for root, dirs, files in os.walk(input_als_dir):
    if root is not input_als_dir:
        for filename in files:
            if (filename.lower().endswith('.hdp')):
                hdp_filename = os.path.join(root, filename)

                # Extract sample file name from hdp
                with open(hdp_filename, 'rb') as f_hdp:
                    # Position of sample filename
                    f_hdp.seek(60)
                    # Read until zero byte
                    sample_path_win = b''.join(iter(lambda: f_hdp.read(1), b'\x00')).decode('utf-8')

                sample_filename = sample_path_win.split('\\')[-1]

                # Calc relpaths
                hdp_relpath = os.path.relpath(hdp_filename, input_als_dir)
                sample_relpath = os.path.join(os.path.relpath(root, input_als_dir), sample_filename)
                log.info('%s -> %s' % (hdp_relpath, sample_relpath))

                # Store in dictionary
                hdp_dict[filename] = sample_relpath

# Read and parse element tree
with gzip.open(input_als) as f_input:
    content = f_input.read()
    xeRoot = ET.fromstring(content) # type: ET.ElementTree

# Find and correct audio clips and sample refs
for xeFileRef in xeRoot.findall('.//SampleRef/FileRef'): # type: ET.Element
    xeName = xeFileRef.find('Name') # type: ET.Element
    name = xeName.get('Value') # type: str
    if (name.lower().endswith('.hdp')):
        # Lookup hdp name in dictionary
        sample_relpath = hdp_dict[name] # type: str
        sample_relpath_split = sample_relpath.split(os.sep)
        sample_relpaths = sample_relpath_split[:-1]
        sample_filename = sample_relpath_split[-1]

        # Correct sample filename
        xeName.set('Value', sample_filename)

        # Rewrite relative paths
        xeRelativePath = xeFileRef.find('RelativePath')
        if xeRelativePath is None:
            xeRelativePath = ET.Element('RelativePath')
            xeFileRef.append(xeRelativePath)

        for xeRelativePathElement in xeRelativePath.findall('RelativePathElement'):
            xeRelativePath.remove(xeRelativePathElement)

        for relpart in sample_relpaths:
            xeRelativePath.append(ET.Element('RelativePathElement', {'Dir': relpart }))

xt = ET.ElementTree(xeRoot)

with gzip.open(output_als, 'wb') as f_output:
    xt.write(f_output, encoding ='utf-8', xml_declaration = True)

log.info("Converted successfully.")


