#!/bin/bash
usage()
{
echo "msprep.sh [-o obsnum] [-c calibration sol] [-d dependancy]
    -o  obsnum   : the observation id
    -c  cal sol  : the calibration solution
    -d dependancy: dependant job id" 1>&2;
exit 1;
}

obsnum=
calibration=
account="mwasci"
machine="garrawarla"
dep=

while getopts "o:c:d:" OPTION
do
    case "$OPTION" in
        o)
            obsnum=${OPTARG}
            ;;
        c)
            calibration=${OPTARG}
            ;;
        d)
            dep=${OPTARG}
            ;;
        ? | : | h)
            usage
            ;;
    esac
done

# pring for help if obsid or calibration solution not given
if [[ -z ${obsnum} ]]
then
    usage
fi

if [[ -z ${calibration} ]]
then
    usage
fi

if [[ ! -z ${dep} ]]
then
    depend="--dependency=afterok:${dep}"
fi

## load configurations
source bin/config.txt

## run template script
script="${MYBASE}/queue/msprep_${obsnum}.sh"
cat ${base}bin/msprep.sh | sed -e "s:OBSNUM:${obsnum}:g" \
                                -e "s:BASE:${MYBASE}:g" \
                                -e "s:CALIBRATIONSOL:${calibration}:g" \
                                -e "s:MYPATH:${MYPATH}:g"> ${script}

output="${base}queue/logs/msprep_${obsnum}.o%A"
error="${base}queue/logs/msprep_${obsnum}.e%A"
sub="sbatch --begin=now+15 --output=${output} --error=${error} ${depend} -J msprep_${obsnum} -M ${MYCLUSTER} ${script}"
jobid=($(${sub}))
jobid=${jobid[3]}

# rename the err/output files as we now know the jobid
error=`echo ${error} | sed "s/%A/${jobid}/"`
output=`echo ${output} | sed "s/%A/${jobid}/"`

echo "Submitted msprep job as ${jobid}"