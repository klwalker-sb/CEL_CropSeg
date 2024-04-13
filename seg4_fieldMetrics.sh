#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -n 4 # number of cores
#SBATCH -t 0-08:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o fldFts.%N.%a.%j.out # STDOUT
#SBATCH -e fldFts.%N.%a.%j.err # STDERR
#SBATCH --job-name="fldFts"

####################################
####Set permissions of output files:
umask 002
####################################

## set parameters in seg0_config.sh
source seg0_config.sh

cd ~/
conda activate .cultionet38
python code/bash/seg_utils/seg4_fieldMetrics.py $instance_method $thresholds $VERSION_DIR $grid_file
conda deactivate




