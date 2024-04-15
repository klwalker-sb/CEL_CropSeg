#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -n 4 # number of cores
#SBATCH -t 0-08:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o fldAcc.%N.%a.%j.out # STDOUT
#SBATCH -e fldAcc.%N.%a.%j.err # STDERR
#SBATCH --job-name="fldAcc"

####################################
####Set permissions of output files:
umask 002
####################################

## set parameters in seg0_config.sh
source seg0_config.sh

cd ~/
conda activate .cultionet38
python code/bash/seg_utils/seg5_chipAcc.py $VERSION_DIR $INSTANCE_METHOD $CUTOFFstr $TRAINING_POLYS $ACCURACY_ID_FILE $OUT_ACC_DIR
conda deactivate





