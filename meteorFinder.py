#!/usr/bin/env python
from __future__ import division, print_function
from astropy.io import fits
from astropy.wcs import WCS
import numpy as np
from argparse import ArgumentParser
from datetime import datetime, timedelta
from astropy.coordinates import AltAz, SkyCoord, EarthLocation
import astropy.units as u
import matplotlib.pyplot as plt
import csv

def getNoise(img):
    tmp = np.copy(img)

    tmp[np.abs(tmp) >= 3*np.nanstd(tmp)] = 0 
    tmp[np.abs(tmp) >= 3*np.nanstd(tmp)] = 0 

    return np.nanstd(tmp)


def mask_outside_radius(data, radius=670, fill_value=np.nan):

    data = np.asarray(data)
    ny, nx = data.shape

    yc, xc = ny // 2, nx // 2
    yy, xx = np.ogrid[:ny, :nx]

    r2 = (yy - yc)**2 + (xx - xc)**2
    mask = r2 > radius**2

    masked = data.astype(float).copy()
    masked[mask] = fill_value
    return masked



def mask_below_elevation(data, wcs, elev_min_deg=20.0,
                         location=None, obstime=None):

    ny, nx = data.shape
    y, x = np.mgrid[0:ny, 0:nx]   # pixel coordinates

    # pixel -> RA/Dec (degrees)
    ra, dec = wcs.all_pix2world(x, y, 0)
    coord = SkyCoord(ra, dec, unit=(u.deg,u.deg))
    coord.time = obstime + timedelta(hours=location.lon.hourangle)
    altaz = coord.transform_to(AltAz(obstime=obstime, location=location))

    elev = altaz.alt.deg  # elevation in degrees
    az = altaz.az.deg  # elevation in degrees

    mask = elev < elev_min_deg
    masked = data.copy().astype(float)
    masked[mask] = np.nan  # or whatever flag value you prefer

    return masked, ra, dec, az, elev


def makeDiffTemplates():

    ## 24 templates to make
    diff_cube = []

    for i in range(24):

        cube = []
        for IF in range(32):

            f = i*32 + IF
            
            ## skip edge channels
            if IF in [0, 1, 30, 31]:
                continue
            
            hdu = fits.open('img-{}-image.fits'.format(str(f).zfill(4)))
            data = hdu[0].data[0,0,:,:]
            cube.append(data)
        
        diff = np.nanmedian(np.array(cube), axis=0)
        diff_cube.append(diff)

    return np.array(diff_cube)
        
            
def getFlagChannels():
    flag_indices = []
    for i in range(24):
        base = i * 32
        flag_indices += [base + 0, base + 1, base + 30, base + 31]

    return np.array(flag_indices)

def floodfill(seed_row, seed_col, snr_map, diff, ra_map, dec_map, az_map, el_map, floodfillSigma, imgSize):
    """
    forest fire floodfill
    """

    q = []
    q.append([seed_row, seed_col])

    ## initialise output arrays
    row_array = []
    col_array = []
    ra_array = []
    dec_array = []
    az_array = []
    el_array = []
    s_array = []
    snr_array = []

    while q:
        row, col = q.pop()
        binaryMapTemp[row, col] = 1

        row_array.append(row)
        col_array.append(col)
        ra_array.append(ra_map[row, col])
        dec_array.append(dec_map[row, col])
        az_array.append(az_map[row, col])
        el_array.append(el_map[row, col])
        s_array.append(diff[row, col])
        snr_array.append(snr_map[row, col])

        ## check if we are at the edge of the image
        if row == 0 or row == imgSize -1:
            continue
        if col == 0 or col == imgSize - 1:
            continue

        ## search nearby pixels
        test_row, test_col = row + 1, col
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row , col + 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row - 1, col
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row, col - 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])


        test_row, test_col = row + 1, col + 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row - 1, col + 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row + 1, col - 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

        test_row, test_col = row - 1, col - 1
        if snr_map[test_row, test_col] >= floodfillSigma and binaryMapTemp[test_row, test_col] == 0:
            q.append([test_row, test_col])

    return np.array(row_array), np.array(col_array), np.array(ra_array), np.array(dec_array), np.array(az_array), np.array(el_array), np.array(s_array), np.array(snr_array)

def main(args):

    ## invidialse output arrays
    global binaryMapTemp
    binaryMapTemp = np.zeros((args.imgSize, args.imgSize))
    loc = EarthLocation(lon=116.67083333*u.deg, lat=-26.70331941*u.deg, height=377.827*u.m)   

    ## initialise output arrays
    utc_array = []
    f_array = []
    #ch_array = []
    noise_before_array = []
    noise_after_array = []
    no_pixels_array = []
    peak_snr_array = []
    #row_array = [] 
    #col_array = [] 
    ra_array = [] 
    dec_array = [] 
    #az_array = [] 
    #el_array = [] 
    s_peak_array = [] 
    s_int_array = [] 
    #snr_array = []
        

    ## make background templates
    if args.verbose:
        print('making difference templates')
    diff_cube = makeDiffTemplates()
    if args.verbose:
        print('Done.')

    flag_channels = getFlagChannels()

    #if args.verbose:
    #    iterator = tqdm(range(args.freqChannels))
    #else:
    iterator = range(args.freqChannels)

    for f in iterator:

        ## skip if edge channel
        if f in flag_channels:
            continue

        coarse_channel = f//32

        hdu = fits.open('img-{}-image.fits'.format(str(f).zfill(4)))
        data = hdu[0].data[0,0,:,:]
        wcs = WCS(hdu[0].header, naxis=2)
        t = datetime.strptime(hdu[0].header['DATE-OBS'][:-2], '%Y-%m-%dT%H:%M:%S')   
        diff_bkg = diff_cube[coarse_channel]

        ## discard if either img or diff is flagged
        if np.all(data == 0) or np.all(diff_bkg == 0):
            if args.verbose:
                print('image full of zeros in channel {}'.format(f))
            continue

        if np.any(np.isnan(data)) or np.any(np.isnan(diff_bkg)):
            if args.verbose:
                print('image full of nans in channel {}'.format(f))
            continue

        diff = data - diff_bkg
        noiseDiff = getNoise(diff)

        ## mask everything past horizon
        diff = mask_outside_radius(diff)
        
        ## mask low elevation
        diff, ra_map, dec_map, az_map, el_map = mask_below_elevation(diff, wcs, elev_min_deg=20.0,
                                   location=loc,
                                     obstime=t)
        
        

        maxSNR = np.nanmax(diff)/noiseDiff
        snr_map = diff/noiseDiff

        if maxSNR < args.seedSigma:
            if args.verbose:
                print('No events detected. Max SNR {} in channel {}'.format(maxSNR, f))
            continue
        
        ## get position of seed
        seed_row, seed_col = np.where(diff == np.nanmax(diff))
        seed_row, seed_col = int(seed_row), int(seed_col)

        ## floodfill
        binaryMapTemp = np.zeros((args.imgSize, args.imgSize))
        row_event, col_event, ra_event, dec_event, az_event, el_event, s_event, snr_event = floodfill(seed_row, 
                                                                                                      seed_col, 
                                                                                                      snr_map, diff, ra_map, 
                                                                                                      dec_map, az_map,
                                                                                                        el_map, 
                                                                                                        args.floodfillSigma,
                                                                                                        args.imgSize)
        

        ## append events
        utc_array.append(t)
        #f_array.append(f)
        f_array.append(hdu[0].header['CRVAL3'])
        noise_before_array.append(getNoise(data))
        noise_after_array.append(noiseDiff)
        no_pixels_array.append(len(row_event))
        peak_snr_array.append(maxSNR)
        #row_array.append(row_event)
        #col_array.append(col_event)
        ra_array.append(ra_event)
        dec_array.append(dec_event)
        #az_array.append(az_event)
        #el_array.append(el_event)
        s_peak_array.append(np.max(s_event))
        s_int_array.append(np.sum(s_event))
        #snr_array.append(snr_event)
    
    ## write events to disk
    with open('obs-{}-t-{}.csv'.format(args.obs, args.timeStep), "w") as vsc:
        thewriter = csv.writer(vsc)
        thewriter.writerow(['utc', 'f', 'noise0', 'noise1', 'noPix', 'peakSNR', 'ra', 'dec', 's_peak' ,'s_int'])

        for utc, f_no, noise0, noise1, noPix, peakSNR, ra, dec, s_peak, s_int in zip(utc_array, f_array, 
                                                                                                 noise_before_array, noise_after_array,
                                                                                                 no_pixels_array, peak_snr_array,
                                                                                                ra_array,
                                                                                                 dec_array,
                                                                                                 s_peak_array, s_int_array):
            thewriter.writerow([utc, f_no, noise0, noise1, noPix, peakSNR,  ra, dec, s_peak, s_int])


        



if __name__ == "__main__":
    parser = ArgumentParser('meteorFinder', description='source finding software used to find meteors in MWA data')
    parser.add_argument('--obs', required=True, help='The observation ID')
    parser.add_argument('--timeStep', required=True, type=int, help='The timestep at which sourcefinding runs')
    parser.add_argument('--freqChannels', default=768, type=int, help='Number of frequency channels to process')
    parser.add_argument('--seedSigma', default=10, type=float, help='The sigma threshold for RFI seeding')
    parser.add_argument('--floodfillSigma', default=3, type=float, help='The sigma upto which floodfill happens')
    parser.add_argument('--imgSize', required=True, type=int, help='The img size of input fits')
    parser.add_argument('--verbose', default=False, type=bool, help='If true, prints out lots of stuff')
    args = parser.parse_args()

    if args.verbose:
        print('Running source finding in verbose mode for timestep {}.'.format(args.timeStep))

    main(args)
