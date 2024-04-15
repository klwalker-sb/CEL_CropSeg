#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -t 3-00:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o CNtrPY.%N.%a.%j.out # STDOUT
#SBATCH -e CNtrPY.%N.%a.%j.err # STDERR
#SBATCH --job-name="CNtrPY" ## CNtrEU ##CNtrPY

####Set permissions of output files:
umask 002




## set parameters in seg0_config.sh
source seg0_config.sh




cd ~/
source .bashrc
conda activate .cultionet38

## 1) create list of regions that have finished time series chips 
python ~/code/bash/seg_utils/cnet_ready_regions.py $VERSION_DIR $VIstring

## 2) create pytorch training dataset from 1)
cd $VERSION_DIR/
cultionet create --project-path . -gs 100 100 --destination train --start-date $MMDD --end-date $MMDD --config-file "${VERSION_DIR}/config_cultionet.yml" --max-crop-class 1 $EXTRA_ARGS_create

## 3) train ResUnet using pytorch training data from 2)
cultionet train -p . --val-frac $VAL_FRAC --random-seed $SEED --batch-size $BATCH_SIZE --epochs $NUM_EPOCHS -lr $LEARNING_RATE --start-date $MMDD --end-date $MMDD --device $CPU_GPU

conda deactivate



## PROJECT_PATH="/home/downspout-cel/paraguay_lc/Segmentations/AI4Boundaires/"
## EU cli: cultionet train -p . --val-frac 0.2 --random-seed 130 --batch-size 8 --epochs 50 -lr 0.001 -sd 01-01 -ed 01-01
## EU transfer testin: cultionet train --project-path . --val-frac 0.2 --epochs $NUM_EPOCHS --accumulate-grad-batches 1 --model-type ResELUNetPsi --activation-type SiLU --res-block-type res --attention-weights spatial_channel --filters 32 --device gpu --processes 2 --load-batch-workers 2 --batch-size 8 --precision 16 --deep-sup-dist --deep-sup-edge --deep-sup-mask --lr-scheduler OneCycleLR
## cultionet train-transfer -p . --val-frac 0.2 --batch-size 8 --epochs 150 -lr 0.00001 -sd 07-01 -ed 07-01 --finetune
## 3) train-transfer ResUnet using pytorch training data from 2) 
## PY cli: cultionet train-transfer -p . --val-frac 0.2 --random-seed 130 --batch-size 8 --epochs 50 -lr 0.00001 -sd 07-01 -ed 07-01
## orig tsfr: 
## patience:50 epochs:150 lr:0.0001: cultionet train-transfer -p . --val-frac $VAL_FRAC --random-seed $SEED --batch-size $BATCH_SIZE -sd $SD -ed $ED $EXTRA_ARGS_train --patience 50 --epochs 150 -lr 0.0001
## cultionet train-transfer -p . --val-frac $VAL_FRAC --random-seed $SEED --batch-size $BATCH_SIZE -sd $SD -ed $ED $EXTRA_ARGS_train --patience 50 --epochs 150 -lr 0.0001

