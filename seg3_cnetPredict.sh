#!/bin/bash -l

#SBATCH -N 1 # number of nodes
#SBATCH -t 0-08:00 # time (D-HH:MM)
#SBATCH -p basic
#SBATCH -o PY3n.%N.%a.%j.out # STDOUT
#SBATCH -e PY3n.%N.%a.%j.err # STDERR
#SBATCH --job-name="PY3n"
#SBATCH --array=[001]%1


####################################
####Set permissions of output files:
umask 002
####################################

## set grid ID parameter 
### GRID_ID=$(($SLURM_ARRAY_TASK_ID + 4000)) 
GRID_ID=$(($SLURM_ARRAY_TASK_ID + 3000)) 



##3k: [000,001,002,003,004,005,007,008,009,010,011,022,023,028,029,030,031,032,034,060,080,095,115,121,122,123,124,180,182,183,184,185,204,208,213,214,216,217,218,219,237,247,249,250,266,270,275,279,280,284,313,314,315,316,318,319,320,321,351,356,357,358,359,370,371,395,396,397,398,399,401,402,403,404,406,407,410,411,412,431,432,439,440,441,442,443,444,445,446,447,448,454,455,456,457,458,459,487,489,490,491,492,493,494,495,496,500,501,502,503,504,505,506,507,515,517,524,535,537,540,541,542,543,549,550,551,552,553,554,555,556,557,585,586,588,589,590,591,592,593,595,596,597,598,599,600,601,602,603,604,605,606,607,608,609,615,624,627,628,629,630,631,632,633,635,636,637,638,639,640,641,642,643,644,645,646,647,648,649,650,651,652,653,654,655,656,657,658,659,674,675,676,677,678,679,680,681,682,683,684,685,686,687,688,689,690,691,692,693,694,695,696,697,698,699,700,701,702,703,704,705,706,707,710,711,712,713,714,715,716,717,718,719,720,721,722,723,724,725,726,727,728,729,730,731,732,733,734,735,736,737,738,739,740,741,742,743,747,748,749,750,751,752,753,754,755,756,757,758,759,760,761,762,763,764,765,766,767,768,769,770,771,772,773,774,775,776,777,778,779,782,783,784,785,786,787,788,789,790,791,792,793,794,795,796,797,798,799,800,801,802,803,804,805,806,807,808,809,810,811,812,813,814,818,819,820,821,822,823,824,825,826,827,828,829,830,831,832,833,834,835,836,837,838,839,840,841,842,843,844,845,846,847,848,853,854,855,856,857,858,859,860,861,862,863,864,865,866,867,868,869,870,871,872,873,874,875,876,877,878,879,880,881,882,883,884,885,888,889,890,891,892,893,894,895,896,897,898,899,900,901,902,903,904,905,906,907,908,909,910,911,912,913,914,915,916,917,918,919,920,923,924,925,926,927,928,929,930,931,932,933,934,935,936,937,938,939,940,941,942,943,944,945,946,947,948,949,950,951,952,953,957,958,959,960,961,962,963,964,965,966,967,968,969,970,971,972,973,974,975,976,977,978,979,980,981,982,983,984,985,986,989,990,991,992,993,994,995,996,997,998,999]


##4k: [000,001,002,003,004,005,006,007,008,009,010,011,012,013,014,015,016,026,027,028,029,030,031,032,033,034,035,036,037,038,039,040,041,042,043,045,046,047,048,049,050,051,052,053,054,055,056,057,058,059,060,061,065,066,067,068,069,070,071,072,073,074,075,076,077,078,079,084,085,086,087,088,089,090,091,092,097,098,099,100,101,102]






#########################
##### do not change below 

## set parameters in seg0_config.sh
source seg0_config.sh

PRED_PREFIX="PY_" ## "EUctrl_" ## "PYctrl_" ## "PYtsfr_"

REGION=00${GRID_ID} ## change REGION to save only smaller chip, will look in time_series_vars dir but the images are already copied  

CONFIG_FILE="${VERSION_DIR}/config_cultionet.yml"
OUT_FILE="${VERSION_DIR}/composites_probas/pred_${PRED_PREFIX}${GRID_ID}.tif"
REF_IMG="{VERSION_DIR}/time_series_vars/${REGION}/brdf_ts/ms/${VIs[1],,}/${END_YR}001.tif"
cd ~/
conda activate .cultionet38

python ~/code/bash/seg_utils/cnet_cp_predTS.py $GRID_ID $VERSION_DIR $END_YR $MMDD $VIs $PROJECT_DIR

cd $VERSION_DIR/

cultionet create-predict -p . -y $END_YR -w 100 --padding 110 --ts-path $REGION --append-ts y --image-date-format %Y%j -n 4 --config-file $CONFIG_FILE -sd $MMDD -ed $MMDD

cultionet predict -p . -y $END_YR -o $OUT_FILE -d data/predict/processed/ --region $REGION --ref-image $REF_IMG -g $GRID_ID -w 100 --padding 101 --device $CPU_GPU --batch-size 4 -sd $MMDD -ed $MMDD --config-file $CONFIG_FILE


conda deactivate











######################### EU 

## GRID_DIR="/home/downspout-cel/paraguay_lc/Segmentations/AI4Boundaires/grid"
## VERSION_DIR="/home/downspout-cel/paraguay_lc/Segmentations/AI4Boundaires"
## GEOREF_IMG="${VERSION_DIR}/time_series_vars/${REGION}/brdf_ts/ms/evi2/2020001.tif"
## PRED_YR=2020 
## ED="01-01"
## SD="01-01"  




## PY cli: cultionet predict -p . -y 2021 -o /home/downspout-cel/paraguay_lc/Segmentations/composites_probas/ctrl_003949.tif -d data/predict/processed/ --region 003949 --ref-image /home/downspout-cel/paraguay_lc/Segmentations/time_series_vars/003949/brdf_ts/ms/evi2/2021001.tif -g 3949 -w 100 --padding 101 --config-file /home/downspout-cel/paraguay_lc/Segmentations/config_cultionet.yml  --device cpu --precision 32 --batch-size 8 -sd 07-01 -ed 07-01 
## cultionet predict -p . -y $PRED_YR -o $OUT_NAME -d data/predict/processed/ --region $REGION --ref-image $GEOREF_IMG -g $GRID_ID -w 100 --padding 101 --config-file $CONFIG_FILE  --device cpu --precision 32 --batch-size 8 -sd $SD -ed $ED $EXTRA_ARGS_pred
## EU
## cultionet predict -p . -y $PRED_YR -o $OUT_NAME -d data/predict/processed/ --region $REGION --ref-image $GEOREF_IMG -g $GRID_ID -w 100 --padding 101 --config-file $CONFIG_FILE  --device cpu --precision 32 --batch-size 8 -sd $SD -ed $ED $EXTRA_ARGS_pred

## 3) predict-transfer on grid 
## PY cli: cultionet predict-transfer -p . -y 2021 -o /home/downspout-cel/paraguay_lc/Segmentations/composites_probas/tsfr_003949.tif -d data/predict/processed/ -sd 07-01 -ed 07-01 --region 003949 --ref-image /home/downspout-cel/paraguay_lc/Segmentations/time_series_vars/003949/brdf_ts/ms/evi2/2021001.tif -g 3949 -w 100 --padding 101 --config-file /home/downspout-cel/paraguay_lc/Segmentations/config_cultionet.yml --device cpu --precision 32 --batch-size 8 --load-batch-workers 2 
##cultionet predict-transfer -p . -y $PRED_YR -o $OUT_NAME -d data/predict/processed/ -sd $SD -ed $ED --region $REGION --ref-image $GEOREF_IMG -g $GRID_ID -w 100 --padding 101 --config-file $CONFIG_FILE --device cpu --precision 32 --batch-size 8 --load-batch-workers 2 $EXTRA_ARGS_pred 

 
## test EU -> PY: use regular .cultionet38 environment to predict (not predict-transfer) w/ EU's last.ckpt 




