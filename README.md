#### CREATE CULTIONET ENVIRONMENT  
> conda create --name .cnet38 python=3.8  
> conda activate .cnet38   
> conda config --add channels conda-forge  
> conda config --set channel_priority strict  
> conda install cython>=0.29.* numpy<=1.21.0  
> pip install torch==1.12.1+cu113 torchvision==0.13.1+cu113 torchaudio==0.12.1 --extra-index-url https://download.pytorch.org/whl/cu113 --no-cache-dir    
> python -c "import torch;print(torch.cuda.is_available())" # GPU check: True if cuda/GPU is available. if False, make sure you're not on bellows  
> pip install torch-scatter torch-sparse torch-cluster torch-spline-conv torch-geometric torch-geometric-temporal  --extra-index-url https://data.pyg.org/whl/torch-1.12.1%2Bcu113.html --no-cache-dir  
> conda install -c conda-forge gdal  
> pip install cultionet@git+https://github.com/jgrss/cultionet.git  
> cultionet train -h #### cultionet install check

see [cultionet repo](https://github.com/jgrss/cultionet) for training data & config file requirements  

## STEPS TO CREATE CROP FIELD INSTANCES & FIELD SIZE METRICS  
<b>1. copy files from this repo into ```~/code/bash```   
2. fill out seg0_config.sh file with version settings   
3. run seg0-seg5, only updating #SBATCH --array GRID_ID in seg1 & seg3   
</b> 

> cd ~/    
> git clone https://github.com/laurensharwood/CEL_CropSeg.git    
> mv -r CEL_CropSeg/* ~/code/bash   
> rm -r CEL_CropSeg    
> cd ~/code/bash   
> ##### update seg0_config version parameters   
> vim seg0_config.sh  
> sbatch seg0_config.sh   
> ##### update #SBATCH --array GRID_ID for training chip regions to prep   
> sbatch seg1_prepTrain_TS.sh  
> sbatch seg2_cnetTrain.sh   
> ##### update #SBATCH --array GRID_ID for prediction grid cells to predict    
> sbatch seg3_cnetPredict.sh    
> sbatch sbatch seg4_fieldMetrics.sh  
> sbatch sbatch seg5_chipAcc.sh   

 
   
#### <b>seg0_config</b>     
* splits training digitizations -- polys and chips --  by region into ```~/code/bash/seg_utils/cultionetTEMP/user_train```  
* copies cultionetTEMP template from seg_utils folder to {VERSION_DIR}    
* updates {VERSION_DIR}/config_cultionet.yml using seg0_config.sh settings         

#### <b>seg1_prepTrain_TS</b>    
* <b>update #SBATCH --array GRID_ID in bash script</b>       
* for each UNQ GRID_ID ID that contains a 1km training chip, save time-series in ```{VERSION_DIR}/time_series_vars/{REGION}``` -- clip to chip shape, named {REGION}, or clip and mosaic where chip overlaps more than one UNQ GRID_ID cell        

#### <b>seg2_cnetTrain</b>    
* saves list of regions that have completed time series as cnet_training_regions.txt, which is used by config_cultionet.yml in the following step   
* 'cultionet create' makes pytorch (.pt) training for each chip in ```{VERSION_DIR}/data/train/``` referencing config_cultionet.yml, ```{VERSION_DIR}/user_train``` chips & polys, and ```{VERSION_DIR}/time_series_vars``` veg indices 
     
* 'cultionet train' trains resunet model using training params from seg0_config.sh, saves model checkpoint in  ```ckpt```   

#### <b>seg3_cnetPredict</b>     
* <b>update #SBATCH --array GRID_ID in bash script</b>        
* copies time-series for 20km x 20km UNQ GRID_ID cells into ```{VERSION_DIR}/time_series_vars/00{GRID_ID}/brdf_ts/ms/{VI}```       
* 'cultionet create-predict' saves pytorch prediction files for each 20km UNQ GRID_ID cell in #SBATCH --array in ```{VERSION_DIR}/data/predict/processed```   
* 'cultionet predict' runs inference on UNQ GRID_ID cells, save 4band predictions in ```{VERSION_DIR}/composites_probas``` where b1=crop extent probability, b2=distance to border, b3=border probability, and b4 is blank     

#### <b>sbatch seg4_fieldMetrics</b>    
* save single-band inference rasters -- 1:distance to border, 2:extent into ```feats```  
* create vectors of crop field instances in  ```{VERSION_DIR}/infer_polys```   to calculate field size metrics -- 3:area, 4:area/perimeter(APR), 5:texture(seasonal stDev) -- then convert to rastert in ```{VERSION_DIR}/feats```  

#### <b>sbatch seg5_chipAcc</b>    
* calculate per-chip accuracy metrics compared to reference(training digitizations)       
