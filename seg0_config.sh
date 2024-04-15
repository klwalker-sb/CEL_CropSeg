#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -t 3-00:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o cnetCFG.%N.%a.%j.out # STDOUT
#SBATCH -e cnetCFG.%N.%a.%j.err # STDERR
#SBATCH --job-name="cnetCFG"



###################### segmentation parameters 
#### VERSION 
######################

## a) segmentation version directory -- for different years or band combinations 
VERSION_DIR="/home/downspout-cel/paraguay_lc/Segmentations/cnet22_4VI"

## b) segment fields from tri-monthly TS images from the July, 1 before the end year to the July, 1 of the end year  
END_YR=2022

## c) veg indices to use as a bash array -- w/ spaces to delimit items (no commas) and parentheses (no brackets) 
VI_array=("kndvi" "gcvi" "nbr" "ndmi")

## d) update grid ID arrays in seg1_prepTrain_TS.sh and seg3_cnetPredict.sh




########################################################################################
###################### shouldn't need to change parameters below 
########################################################################################

##### PROJECT PARAMS 
## project grid file with 20km x 20km time-series(TS) processing and prediction images
GRID_FILE="/home/downspout-cel/paraguay_lc/Segmentations/PY_grid_8858.gpkg" 
## directory where TS images are located (front padded so each folder has 6 digits)
PROJECT_DIR="/home/downspout-cel/paraguay_lc/stac/grids" 
## MonthDay (with or without dash) to start & end ##PY: "07-01" | ##AI4B EU: "01-01" 
MMDD="07-01"
 ## to name interence rasters PRED_PREFIX+pred... ## PY_" | "PYctrl_"| "EUctrl_" | "PYtsfr_" 
PRED_PREFIX="PY_"

##### TRAINING DIGITIZATIONS 
## field digitization polygons and chip (1km x 1km) shapes (looks for chip shapein the same folder as training_polys, where "_Polys_"is replaced with "_Chips_" 
TRAINING_POLYS="/home/downspout-cel/paraguay_lc/Segmentations/00_digitizations/PyCropSeg_Polys_8858.shp"


#### CULTIONET TRAINING PARAMS
NUM_EPOCHS=10 ###TRAIN-TRANSFER TESTING w/ LEARNING RATE: 100 | 150 | 200
LEARNING_RATE=0.01 ###TRAIN-TRANSFER TESTING w/ 0.001 | 0.0001 | 0.00001 
BATCH_SIZE=8
VAL_FRAC=0.2
SEED=100

CPU_GPU="gpu" ## "gpu" | "cpu"


#### SEMANTIC TO INSTANCE PARAMS
## options: "EO", "threshold", "watershed"
INSTANCE_METHOD="EO" 
## EO requires 1 cutoff value (1 + extent - boundary), threshold requires 2(boundary, extent) , watershed requires 3(boundary, extent, seed size) 
CUTOFFS=(8.5) ## as a bash array to match formatting as VI_array, which needs to be that type for seg1.sh


## file with first column called 'id' to USE in the accuracy assessment --- from the chips that had an incomplete time-series 
ACCURACY_ID_FILE="$VERSION_DIR/cnet_training_regions_holdout.txt"
## directory to save accuracy file 
OUT_ACC_DIR="/home/downspout-cel/paraguay_lc/Segmentations/00_chip_accuracy"
 
 
 
#########################################################################################


cd ~/
source .bashrc
conda activate .cultionet38


## 1) create list of regions that have finished time series chips 
VIstring=$(IFS=','; echo "${VI_array[*]}") ## VI_array as a string separated by commas -- for reading into python functions that need lists 
CUTOFFstr=$(IFS=','; echo "${CUTOFFS[*]}") ## CUTOFFS as a string separated by commas -- for reading into python functions that need lists 
python ~/code/bash/seg_utils/seg0_config.py $VERSION_DIR $END_YR $TRAINING_POLYS $VIstring

