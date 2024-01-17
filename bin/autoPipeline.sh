#!/bin/bash

usage()
{
echo "autoPipeline.sh [-d download link] [-o obsnum] [-c calsol]"
}

obsnum=
account="mwasci"
machine="garrawarla"
link=
calibrationPath=

while getopts "d:o:c:" OPTION
do
    case "$OPTION" in
        d)
            link=${OPTARG}
            ;;
        o)
            obsnum=${OPTARG}
            ;;
        c)
            calibrationPath=${OPTARG}
            ;;
        ? | : | h)
            usage
            ;;
    esac
done

## load configurations
source bin/config.txt

### run download job
script="${MYBASE}/queue/wget_${obsnum}.sh"
cat ${base}bin/wget.sh | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:BASE:${MYBASE}:g" \
                                -e "s:MYPATH:${MYPATH}:g"> ${script}

output="${base}queue/logs/wget_${obsnum}.o%A"
error="${base}queue/logs/wget_${obsnum}.e%A"
sub="sbatch --begin=now+15 --output=${output} --error=${error} -J wget_${obsnum} -M ${MYCLUSTER} ${script} -l ${link}"
jobid=($(${sub}))
jobid=${jobid[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

echo "Submitted wget job as ${jobid}"



### run msprep job
depend="--dependency=afterok:${jobid}"
script="${MYBASE}/queue/msprep_${obsnum}.sh"
cat ${base}bin/msprep.sh | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:BASE:${MYBASE}:g" \
                                -e "s:CALIBRATIONSOL:${calibration}:g" \
                                -e "s:MYPATH:${MYPATH}:g"> ${script}

output="${base}queue/logs/msprep_${obsnum}.o%A"
error="${base}queue/logs/msprep_${obsnum}.e%A"
sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} -J msprep_${obsnum} -M ${MYCLUSTER} ${script}"
jobid1=($(${sub}))
jobid1=${jobid1[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid1}/"`
output=`echo ${output} | sed "s/%A/${jobid1}/"`

echo "Submitted msprep job as ${jobid1}"


### run source find
depend="--dependency=afterok:${jobid1}"
script="${MYBASE}/queue/sourceFind_${obsnum}.sh"
cat ${base}bin/sourceFind.sh | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:BASE:${MYBASE}:g" \
                                -e "s:MYPATH:${MYPATH}:g"> ${script}

output="${base}queue/logs/sourceFind_${obsnum}.o%A"
error="${base}queue/logs/sourceFind_${obsnum}.e%A"
sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} -J sourceFind_${obsnum} -M ${MYCLUSTER} ${script}"
jobid2=($(${sub}))
jobid2=${jobid2[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid2}/"`
output=`echo ${output} | sed "s/%A/${jobid2}/"`

echo "Submitted sourceFind job as ${jobid2}"