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
calObID=CAL
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

rm -r calibrated.ms

TIMESTEPS=30
updatedTIMESTEPS=$(($TIMESTEPS-1)) ## cos indexes start from zero
channels=768 ## hard coded 
updatedCHANNELS=$(($channels-1)) ## cos indexes start from zero

## step 1) applyCalSolution
cp ../${calObID}/${calObID}.bin .
# applysolution --data ${obsnum}.metafits ${obsnum}.ms \
#   -s ${calObID}.bin --outputs calibrated.ms
ao_applysol ${obsnum}.ms ${calObID}.bin

cp ../../meteorFinder.py .

for ((g=0;g<=${updatedTIMESTEPS};g++));
do
    echo "working on timeStep " ${g}
    startt=`date +%s`

    i=$((g*1))
    j=$((i+1))

    wsclean -quiet -name img -size 1400 1400 -abs-mem 120 -interval ${i} ${j} \
      -channels-out ${channels} -weight briggs 0 -scale 5amin -use-wgridder \
      -maxuvw-m 500 -no-dirty ${obsnum}.ms

    endt=`date +%s`
    runtimet=$((endt-startt))
    echo "the imaging run time ${runtimet}"


    startt=`date +%s`
    ## source find
    myPython ./meteorFinder.py --obs ${obsnum} --timeStep ${i} --freqChannels 768 --imgSize 1400
    endt=`date +%s`
    runtimet=$((endt-startt))
    echo "sourceFinding run time ${runtimet}"

    rm img*.fits

done

end=`date +%s`
runtime=$((end-start))
echo "the job run time ${runtime}"

  
}