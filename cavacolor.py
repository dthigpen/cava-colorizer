import argparse
import configparser
import json
from pathlib import Path
import random
from subprocess import call

from PIL import Image
import numpy as np
import requests
from io import BytesIO
import scipy
import scipy.misc
import scipy.cluster

#defaults
cavaConfigPath = str(Path.home()) + '/.config/cava/config'
gpmdpConfigPath = str(Path.home()) + '/.config/Google Play Music Desktop Player/json_store/playback.json'
reloadConfigCmd = 'pkill -USR1 cava'
NUM_CLUSTERS = 5

parser = argparse.ArgumentParser()
parser.add_argument('--cava',help='The path to the cava config file. Default is %s' % cavaConfigPath)
parser.add_argument('--gpmdp',help='The path to the Google Play Music Desktop Player config file. Default is %s' % gpmdpConfigPath)
parser.add_argument('-f','--foreground',help='The foreground color will be set using this flag.')
parser.add_argument('-b','--background',help='The background color will be set using this flag.')

args = parser.parse_args()

if args.cava:
    cavaConfigPath = args.cava
if args.gpmdp:
    gpmdpConfigPath = args.gpmdp

config = configparser.ConfigParser()
config.read(cavaConfigPath)
with open(gpmdpConfigPath,'r') as playbackFile:
    albumurl = json.load(playbackFile)['song']['albumArt']
    response = requests.get(albumurl)
    im = Image.open(BytesIO(response.content))
    # print('Image size: ', im.size)
    im = im.resize((150, 150))      # optional, to reduce time
    ar = np.asarray(im)
    shape = ar.shape
    ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)
    codes, dist = scipy.cluster.vq.kmeans(ar, NUM_CLUSTERS)

    vecs, dist = scipy.cluster.vq.vq(ar, codes)         # assign codes
    counts, bins = scipy.histogram(vecs, len(codes))    # count occurrences

    index_max = scipy.argmax(counts)                    # find most frequent
    colorRGB = codes[index_max].astype(int)
    colorHex = '#%02x%02x%02x' % tuple(colorRGB)

    config['color']['foreground'] = "'%s'" % colorHex
    
    print(config['color']['foreground'])
    print(config['color']['background'])

    with open(cavaConfigPath,'w') as configfile:
        config.write(configfile)
    call(reloadConfigCmd.split())