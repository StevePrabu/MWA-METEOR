#!/bin/bash -l
#SBATCH --export=NONE
#SBATCH --partition=mwa
#SBATCH --account=mwasci
#SBATCH --ntasks=32
#SBATCH --mem=128GB
#SBATCH --time=24:00:00
#SBATCH --mail-type FAIL,TIME_LIMIT
#SBATCH --mail-user sirmcmissile47@gmail.com

## load modules
module load singularity/4.1.0-slurm
module load giant-squid/2.3.0
shopt -s expand_aliases
source /scratch/mwasci/sprabu/MWA-METEOR/aliases

set -x
{

obsnum=OBSNUM
base=BASE
model=CAL
scratchID=$(giant-squid list -n ${obsnum} | awk '/^[|] [0-9]+/ {print $2}')

cd ${base}/processing

## create folder
if [ -d "${obsnum}" ]; then
  echo "${obsnum} folder does exist."
else
  mkdir ${obsnum}
fi

cd ${obsnum}

## copy data using scratch id
if [ -d "${obsnum}.ms" ]; then
  echo "measurement set already exists."
else
  cp -r /scratch/mwasci/asvo/${scratchID}/* ${base}/processing/${obsnum}
fi

## step 1) run aoflagger
aoflagger ${obsnum}.ms

if [ -f "round1.bin" ]; then
  echo "calibration file already exits"
else
  ## step 2) calibrate using source model
  calibrate -d ${obsnum}.ms ${obsnum}.metafits -s ../../models/model-${model}-*_withalpha.txt \
    -o round1.bin --uvw-min 10m --uvw-max 2000m \
    --beam-file /scratch/mwasci/sprabu/MWA-METEOR/containers/mwa_full_embedded_element_pattern.h5
fi

if [ -f "round1*.png" ]; then
  echo "calibration plots already exits"
else
  ## step 3) plot calibration solution
  plotsolution round1.bin
fi

if [ -d "calibrated.ms" ]; then
  echo "calibrated ms exits"
else
  ## step 4) apply solutions
  applysolution --data ${obsnum}.metafits ${obsnum}.ms \
  -s round1.bin --outputs calibrated.ms
fi

### self cal
wsclean -name selfcal -size 1000 1000 -scale 50asec -weight natural \
  -niter 10000 -mgain 0.2 -auto-threshold 1.5 -pol I -apply-primary-beam \
  -mwa-path /scratch/mwasci/sprabu/MWA-METEOR/containers -maxuvw-m 2000 \
  -minuvw-m 50 -circular-beam calibrated.ms/ 

aocal -absmem 120 -minuv 10 -maxuv 2000 -ch 4 \
  -applybeam -mwa-path /pawsey/mwa calibrated.ms ${obsnum}.bin

ao_applysol calibrated.ms ${obsnum}.bin

plotsolution ${obsnum}.bin

wsclean -name after-selfcal -size 1000 1000 -scale 50asec -weight natural \
  -niter 10000 -mgain 0.2 -auto-threshold 1.5 -pol I -apply-primary-beam \
  -mwa-path /scratch/mwasci/sprabu/MWA-METEOR/containers -maxuvw-m 2000 \
  -minuvw-m 50 -circular-beam calibrated.ms/ 

}