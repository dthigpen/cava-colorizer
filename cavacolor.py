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

# defaults
cavaConfigPath = str(Path.home()) + '/.config/cava/config'
gpmdpConfigPath = str(Path.home()) + '/.config/Google Play Music Desktop Player/json_store/playback.json'
reloadConfigCmd = 'pkill -USR1 cava'
NUM_CLUSTERS = 5
CENTER_WIDTH_PERC = 0.35
CENTER_HEIGHT_PERC = 0.35
# Measured in luminescence 
EXCLUDE_DARKS_THRESH = 60
EXCLUDE_LIGHTS_THRESH = 10

def openPlaybackInfo(pathToInfoFile):
    with open(gpmdpConfigPath,'r') as playbackFile:
        return json.load(playbackFile)
    return None

def getColorCounts(image, focusCenter = False, darkThreshold = None, lightThreshold = None):

    ar = np.asarray(image)
    if focusCenter:
        y, x, z = ar.shape
        centerWidth = int(x*CENTER_WIDTH_PERC)
        centerHeight = int(y*CENTER_HEIGHT_PERC)
        startx = x//2-(centerWidth//2)
        starty = y//2-(centerHeight//2)    
        ar = ar[starty:starty+centerHeight,startx:startx+centerWidth]
    
    shape = ar.shape
    ar = ar.reshape(scipy.product(shape[:2]), shape[2]).astype(float)

    codes, dist = scipy.cluster.vq.kmeans(ar, NUM_CLUSTERS)
    print(len(codes))
    if darkThreshold != None:
        codes = excludeDarks(codes, darkThreshold)
    if lightThreshold != None:
        codes = excludeLights(codes, lightThreshold)

    print(len(codes))
    print(codes)
    if(len(codes) == 0):
        return [], []
    else:
        vecs, dist = scipy.cluster.vq.vq(ar, codes)         # assign codes
        
        counts, bins = scipy.histogram(vecs, len(codes))    # count occurrences
        return codes , counts

def  getLuminescence(colorRGB):
    r = colorRGB[0]
    g = colorRGB[1]
    b = colorRGB[2]
    luma = 0.2126 * r + 0.7152 * g + 0.0722 * b; # per ITU-R BT.709
    return luma

def excludeDarks(colors, threshold):
    if threshold != None:
        return [color for color in colors if getLuminescence(color) > threshold]
    else:
        return colors
def excludeLights(colors, threshold):
    if threshold != None:
        return [color for color in colors if getLuminescence(color) < threshold]
    else:
        return colors

def favorDarks(colors):
    pass

def favorLights(colors):
    pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--cava',help='The path to the cava config file. Default is %s' % cavaConfigPath)
    parser.add_argument('--gpmdp',help='The path to the Google Play Music Desktop Player config file. Default is %s' % gpmdpConfigPath)
    parser.add_argument('-ed','--excludedarks',nargs='?',const=EXCLUDE_DARKS_THRESH, type=int, help='Excludes the darker colors in the image. The default luminescence threshhold is 60.')
    parser.add_argument('-el','--excludelights',nargs='?',const=EXCLUDE_LIGHTS_THRESH, type=int, help='Excludes the lighter colors in the image. The default luminescence threshhold is 10.')
    parser.add_argument('-c','--center',action='store_true', help='Center the color reading for the foreground around the center of the image')
    
    args = parser.parse_args()
    custom_dark_thresh = args.excludedarks
    custom_light_thresh = args.excludelights
    if args.cava:
        cavaConfigPath = args.cava
    if args.gpmdp:
        gpmdpConfigPath = args.gpmdp

    config = configparser.ConfigParser()
    config.read(cavaConfigPath)

    songInfo = openPlaybackInfo(gpmdpConfigPath)
    if songInfo != None:
        albumurl = songInfo['song']['albumArt']
        response = requests.get(albumurl)
        im = Image.open(BytesIO(response.content))
        codes, counts = getColorCounts(im,focusCenter=args.center, darkThreshold=custom_dark_thresh, lightThreshold=custom_light_thresh)
        
        if len(codes) > 0 and len(counts) > 0:
            index_max = scipy.argmax(counts)                    # find most frequent
            colorRGB = codes[index_max].astype(int)
            colorHex = '#%02x%02x%02x' % tuple(colorRGB)

            config['color']['foreground'] = "'%s'" % colorHex
            print('Foreground color: ', config['color']['foreground'])

            with open(cavaConfigPath,'w') as configfile:
                config.write(configfile)
            call(reloadConfigCmd.split())
        else:
            print('No colors matching requirements')