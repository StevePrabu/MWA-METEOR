#!/bin/bash -l
#SBATCH --export=NONE
#SBATCH -p workq
#SBATCH --time=8:00:00
#SBATCH --ntasks=36
#SBATCH --mem=345GB
#SBATCH --tmp=864GB
#SBATCH --nodes=1
#SBATCH --mail-type FAIL,TIME_LIMIT
#SBATCH --mail-user sirmcmissile47@gmail.com

start=`date +%s`

module load singularity
shopt -s expand_aliases
source /astro/mwasci/sprabu/aliases

set -x
{

obsnum=OBSNUM
base=BASE
myPath=MYPATH
calibration=CALIBRATIONSOL

## Step 0) copy data over to nvme
cp -r ${base}/processing/${obsnum}/${obsnum}.ms /nvmetmp
cp ${base}/processing/${obsnum}/${obsnum}.metafits /nvmetmp
cd /nvmetmp

## Step 1) apply calibration solution
applysolutions ${obsnum}.ms ${calibration}

## Step 2) flag 17th and 18th receiver (clock sync problems)
flagantennae ${obsnum}.ms 140 139 138 137 144 143 142 141 131 130 129 136 135 134 133 128 132

# ## Step 3) getpointing and minw-shift back the pointing
# cp /astro/mwasci/sprabu/path/PawseyPathFiles/pointing.py /nvmetmp
# pointing=$(myPython pointing.py --metafits ${obsnum}.metafits)
# chgcentre ${obsnum}.ms ${pointing}
# chgcentre -zenith -shiftback ${obsnum}.ms

## copy ms back to original path
cp -r /nvmetmp/${obsnum}.ms ${base}/processing/${obsnum}/

end=`date +%s`
runtime=$((end-start))
echo "the job run time ${runtime}"

}