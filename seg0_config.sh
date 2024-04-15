#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -t 3-00:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o seg0.%N.%a.%j.out # STDOUT
#SBATCH -e seg0.%N.%a.%j.err # STDERR
#SBATCH --job-name="seg0"



###################### segmentation parameters 
#### VERSION 
## segmentation version directory -- for different years or band combinations 
VERSION_DIR="/home/downspout-cel/paraguay_lc/Segmentations/cnet22_4VI"


## segment fields from tri-monthly TS images from the July, 1 before the end year to the July, 1 of the end year  
END_YR=2021
MMDD="07-01" ##AI4B EU: "01-01" ##PY: "07-01"


## veg indices to use  
VI_array=("kndvi" "gcvi" "nbr" "ndmi")

## csv with list of UNQ cells to run inference predictions on -- must have 'id' column 
UNQ_pred_list="/home/downspout-cel/paraguay_lc/Segmentations/FebSampCells.csv"  


###################### shouldn't need to change parameters below 


##### PROJECT PARAMS 
## project grid file with 20km x 20km time-series(TS) processing and prediction images
grid_file="/home/sandbox-cel/LUCinLA_grid_8858.gpkg" 
## directory where TS images are located (front padded so each folder has 6 digits)
project_dir="/home/downspout-cel/paraguay_lc/stac/grids/" 


##### TRAINING DIGITIZATIONS 
## field digitization polygons and chip (1km x 1km) shapes (chip shape should be in that same folder and have the same name as training_polys, but with "Chips" replaced for "Polys"
TRAINING_POLYS="/home/downspout-cel/paraguay_lc/Segmentations/digitizations/PyCropSeg_Polys_8858.shp"


#### CULTIONET TRAINING PARAMS
NUM_EPOCHS=10 ###TRAIN-TRANSFER TESTING w/ LEARNING RATE: 100 | 150 | 200
LEARNING_RATE=0.01 ###TRAIN-TRANSFER TESTING w/ 0.001 | 0.0001 | 0.00001 
BATCH_SIZE=8
VAL_FRAC=0.2
SEED=100

CPU_GPU="gpu" ## "gpu" | "cpu"


#### SEMANTIC TO INSTANCE PARAMS
## options: "EO", "threshold", "watershed"
## EO requires 1 threshold in a list, threshold requires 2, watershed requires 3 
instance_method="EO" 
thresholds=[8.5]


## reformat VIs for reading list into seg1 bash script instead of python script -- replace commas for spaces, brackets for parentheses     





cd ~/
source .bashrc
conda activate .cultionet38

## 1) create list of regions that have finished time series chips 
VIstring=$(IFS=','; echo "${VI_array[*]}") ## VI_array as a string separated by commas -- for reading into python functions that need lists 
python ~/code/bash/seg_utils/seg0_config.py $VERSION_DIR $END_YR $TRAINING_POLYS $VIstring

