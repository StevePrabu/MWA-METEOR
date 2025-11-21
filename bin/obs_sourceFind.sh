#!/bin/bash
usage()
{
echo "obs_sourceFind.sh [-o obsnum] [-c cal]
    -o  obsnum       : the observation id
    -c  cal sol      : the calibration solution" 1>&2;
exit 1;
}

obsnum=
cal=

while getopts 'o:c:' OPTION
do
    case "$OPTION" in
        o)
            obsnum=${OPTARG}
            ;;
        c)
            cal=${OPTARG}
            ;;
        ? | : | h)
            usage
            ;;
    esac
done


# if obsid is empty then just pring help
if [[ -z ${obsnum} ]]
then
    echo 'obsnum is missing'
    usage
fi


if [[ -z ${cal} ]]
then
    echo 'calibrator model is missing'
    usage
fi

## load configurations
source config.txt

## run template script
script="${MYBASE}/queue/sourceFind_${obsnum}.sh"
cat ${base}bin/sourceFind.sh | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:CAL:${cal}:g" \
                                -e "s:BASE:${MYBASE}:g"> ${script}

output="${base}queue/logs/sourceFind_${obsnum}.o%A"
error="${base}queue/logs/sourceFind_${obsnum}.e%A"
sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} -J sourceFind_${obsnum} -M ${MYCLUSTER} ${script}"
jobid=($(${sub}))
jobid=${jobid[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

echo "Submitted sourceFind job as ${jobid}"