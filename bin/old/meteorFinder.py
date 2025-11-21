#!/usr/bin/env python
from __future__ import division, print_function
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np
import pandas as pd
from argparse import ArgumentParser

def getNoise(img):
    tmp = np.copy(img)

    tmp[np.abs(tmp) >= 3*np.std(tmp)] = 0 
    tmp[np.abs(tmp) >= 3*np.std(tmp)] = 0 

    return np.std(tmp)


def floodfill(seed_row, seed_col, diff, noise, floodfillSigma, imgSize):
    """
    forest fire floodfill
    """
    q = []
    q.append([seed_row, seed_col])
    
    snr_map = diff/noise

    while q:
        row, col = q.pop()
        binaryMapTemp[row, col] = 1

        ## update output files
        if snr_map[row, col] > binaryMapSNR[row, col]:
            binaryMapSNR[row, col] = np.copy(snr_map[row, col])

        ## check if we are at the edge of the image
        if row == 0 or row == imgSize - 1:
            continue
        if col == 0 or col == imgSize - 1:
            continue


        ## search nearby pixels
        if snr_map[row + 1, col] >= floodfillSigma and binaryMapTemp[row + 1, col] == 0:
            q.append([row + 1, col])

        if snr_map[row, col + 1] >= floodfillSigma and binaryMapTemp[row, col + 1] == 0:
            q.append([row, col + 1])

        if snr_map[row, col - 1] >= floodfillSigma and binaryMapTemp[row, col - 1] == 0:
            q.append([row, col - 1])

        if snr_map[row - 1, col] >= floodfillSigma and binaryMapTemp[row - 1, col] == 0:
            q.append([row - 1, col])

        if snr_map[row + 1, col + 1] >= floodfillSigma and binaryMapTemp[row + 1, col + 1] == 0:
            q.append([row + 1, col + 1])

        if snr_map[row + 1, col - 1] >= floodfillSigma and binaryMapTemp[row + 1, col - 1] == 0:
            q.append([row + 1, col - 1])

        if snr_map[row - 1, col + 1] >= floodfillSigma and binaryMapTemp[row - 1, col + 1] == 0:
            q.append([row - 1, col + 1])

        if snr_map[row - 1, col - 1] >= floodfillSigma and binaryMapTemp[row - 1, col - 1] == 0:
            q.append([row - 1, col - 1])

    return




def main(args):

    ### intialise output arrays
    global binaryMapSNR
    binaryMapSNR = np.zeros((args.imgSize, args.imgSize))
    global binaryMapTemp

    noise_array = []
    

    ### load freq diff maping
    df = pd.read_pickle(args.freqDiffMap)

    for f in range(args.freqChannels):

        hdu = fits.open('img-{}-image.fits'.format(str(f).zfill(4)))
        data = hdu[0].data[0,0,:,:]
        f2diff = int(df['diffChannelIndex'][df['mwaChannelIndex']==f])
        hdu_diff = fits.open('img-{}-image.fits'.format(str(f2diff).zfill(4)))
        data_diff = hdu_diff[0].data[0,0,:,:]

        diff = data - data_diff
        noise = getNoise(diff)

        noise1 = getNoise(data)
        noise2 = getNoise(data_diff)

        
        ## discard if noise is greater than 150 Jy (most likely affected by RFI)
        #if noise1/noise2 > 2 or noise2/noise1 >2:
        #    if args.verbose:
        #        print('Noise threshold triggered in channel {}. Noise {} Jy'.format(f, noise))
        #    continue
        #if noise > 150:
        #    if args.verbose:
        #        print('Noise threshold triggered in channel {}. Noise {} Jy'.format(f, noise))
        #    continue

        ## discard if either img in dff is flagged
        if np.all(data == 0) or np.all(data_diff == 0):
            if args.verbose:
                print('Image full of zeroes in  channel {}'.format(f))
            continue

        if np.any(np.isnan(data)) or np.any(np.isnan(data_diff)):
            if args.verbose:
                print('Image full of nans in channel {}'.format(f))
            continue

        noise_array.append(noise)

        maxSNR = np.nanmax(diff)/noise
        
        if maxSNR < args.seedSigma:
            if args.verbose:
                print('no event detected. Max snr {} in channel {}'.format(maxSNR, f))
            continue
        
        ## get position of max pixel
        seed_row, seed_col = np.where(diff == np.nanmax(diff))
        seed_row, seed_col = int(seed_row), int(seed_col)

        ## check if seed is within horizon
        wcs = WCS(hdu[0].header, naxis=2)
        pixcrd = np.array([[seed_col], [seed_row]], dtype=np.float64).T
        world = wcs.wcs_pix2world(pixcrd, 0)
        ra, dec = world.T
        if np.isnan(ra) or np.isnan(dec):
            continue

        if args.verbose:
            print('event detected at {} snr in channel {}'.format(maxSNR, f))

        ## floodfill
        binaryMapTemp = np.zeros((args.imgSize, args.imgSize))
        floodfill(seed_row, seed_col, diff, noise, args.floodfillSigma, args.imgSize)

    ### save detections to file
    hdu = fits.open('img-{}-image.fits'.format(str(0).zfill(4)))
    hdu_new = fits.PrimaryHDU(binaryMapSNR, header=hdu[0].header)
    hdu_new.writeto('detections-obs-{}-t-{}.fits'.format(args.obs, args.timeStep), overwrite=True)



if __name__ == "__main__":
    parser = ArgumentParser('meteorFinder', description='source finding software used to find meteors in MWA data')
    parser.add_argument('--obs', required=True, help='The observation ID')
    parser.add_argument('--timeStep', required=True, type=int, help='The timestep at which sourcefinding runs')
    parser.add_argument('--freqChannels', default=768, type=int, help='Number of frequency channels to process')
    parser.add_argument('--seedSigma', default=10, type=float, help='The sigma threshold for RFI seeding')
    parser.add_argument('--floodfillSigma', default=3, type=float, help='The sigma upto which floodfill happens')
    parser.add_argument('--imgSize', required=True, type=int, help='The img size of input fits')
    parser.add_argument('--freqDiffMap', default='freqDiffMap.plk', help='The plk file that contains the channels to diff')
    parser.add_argument('--verbose', default=False, type=bool, help='If true, prints out lots of stuff')
    args = parser.parse_args()

    if args.verbose:
        print('Running source finding in verbose mode for timestep {}.'.format(args.timeStep))

    main(args)


