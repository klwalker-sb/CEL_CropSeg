#### CREATE CULTIONET ENVIRONMENT  
> conda create --name .cultionet38 python=3.8  ## .cultionet38 virtual environment called in bash scripts    
* see [cultionet repo](https://github.com/jgrss/cultionet) for [install instructions](https://github.com/jgrss/cultionet?tab=readme-ov-file#installation), training data, & config file requirements     

## STEPS TO CREATE CROP FIELD INSTANCES & FIELD SIZE METRICS  
<b>1. copy files from this repo into ```~/code/bash```   
2. fill out seg0_config.sh file with version settings   
3. run seg0-seg5, only updating #SBATCH --array GRID_ID in seg1 & seg3   
</b> 

> cd ~/    
> git clone https://github.com/laurensharwood/CEL_CropSeg.git ## copy files from this repo locally      
> mv CEL_CropSeg/* ~/code/bash ## move files from this repo into bash directory     
> rm -r CEL_CropSeg ## delete empty directory    
> cd ~/code/bash ## navigate into bash directory to run seg0-seg5.sh     
> vim seg0_config.sh ## update version parameters      
> sbatch seg0_config.sh   
> sbatch seg1_prepTrain_TS.sh ## update #SBATCH --array GRID_ID for training chip regions to prep     
> sbatch seg2_cnetTrain.sh   
> sbatch seg3_cnetPredict.sh ## update #SBATCH --array GRID_ID for prediction grid cells to predict    
> sbatch sbatch seg4_fieldMetrics.sh  
> sbatch sbatch seg5_chipAcc.sh   

 
   
#### <b>seg0_config</b>     
* splits training digitizations -- polys and chips --  by region into ```~/code/bash/seg_utils/cultionetTEMP/user_train```  
* copies cultionetTEMP template from seg_utils folder to {VERSION_DIR}    
* updates {VERSION_DIR}/config_cultionet.yml using seg0_config.sh settings         

#### <b>seg1_prepTrain_TS</b>    
* <b>update #SBATCH --array GRID_ID in bash script</b>       
* for each UNQ GRID_ID that contains a 1km training chip, save time-series in ```{VERSION_DIR}/time_series_vars/{REGION}``` -- clip to chip shape, named {REGION}, or clip and mosaic where chip overlaps more than one UNQ GRID_ID cell        

#### <b>seg2_cnetTrain</b>    
* saves list of regions that have completed time series as cnet_training_regions.txt, which is used by config_cultionet.yml in the following step   
* 'cultionet create' makes pytorch (.pt) training for each chip in ```{VERSION_DIR}/data/train/processed``` referencing config_cultionet.yml, ```{VERSION_DIR}/user_train``` chips & polys, and ```{VERSION_DIR}/time_series_vars``` veg indices 
     
* 'cultionet train' trains resunet model using training params from seg0_config.sh, saves model checkpoint in  ```ckpt```   

#### <b>seg3_cnetPredict</b>     
* <b>update #SBATCH --array GRID_ID in bash script</b>        
* copies time-series for 20km x 20km UNQ GRID_ID cells into ```{VERSION_DIR}/time_series_vars/00{GRID_ID}/brdf_ts/ms/{VI}```       
* 'cultionet create-predict' saves pytorch prediction files for each 20km UNQ GRID_ID cell in #SBATCH --array in ```{VERSION_DIR}/data/predict/processed```   
* 'cultionet predict' runs inference on UNQ GRID_ID cells, save 4band predictions in ```{VERSION_DIR}/composites_probas``` where b1=crop extent probability, b2=distance to border, b3=border probability, and b4 is blank     

#### <b>sbatch seg4_fieldMetrics</b>    
* save single-band inference rasters -- 1:distance to border, 2:extent into ```{VERSION_DIR}/feats```  
* create vectors of crop field instances in  ```{VERSION_DIR}/infer_polys```   to calculate field size metrics -- 3:area, 4:area/perimeter(APR), 5:texture(seasonal stDev) -- then convert to rastert in ```{VERSION_DIR}/feats```  

#### <b>sbatch seg5_chipAcc</b>    
* calculate per-chip accuracy metrics compared to reference(training digitizations)       
