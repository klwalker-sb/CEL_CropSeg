#### CREATE CULTIONET ENVIRONMENT  
> conda create --name .cultionet38 python=3.8  ## .cultionet38 virtual environment called in bash scripts    
* see [cultionet repo](https://github.com/jgrss/cultionet) for [install instructions](https://github.com/jgrss/cultionet?tab=readme-ov-file#installation), training data, & config file requirements     

## STEPS TO CREATE CROP FIELD INSTANCES & FIELD SIZE METRICS  
<b>1. copy files from this repo into ```~/code/bash```   
2. fill out seg0_config.sh file with version settings   
3. run seg0-seg5, only updating #SBATCH --array GRID_ID in seg1 & seg3   
</b> 

```
cd ~/code/bash   
git clone https://github.com/laurensharwood/CEL_CropSeg.git ## copy files from this repo locally      
mv CEL_CropSeg/* . ## move files from this repo into current directory      
rm -r CEL_CropSeg ## delete empty directory (y...)       
vim seg0_config.sh ## update version parameters      
sbatch seg0_config.sh  
sbatch seg1_prepTrain_TS.sh ## update #SBATCH --array GRID_ID for training chip regions to prep     
sbatch seg2_cnetTrain.sh   
sbatch seg3_cnetPredict.sh ## update #SBATCH --array GRID_ID for prediction grid cells to predict    
sbatch sbatch seg4_fieldMetrics.sh  
sbatch sbatch seg5_chipAcc.sh   
```  

Note: If you see the following error while trying to run a bash script... copy contents of the .sh file and recreate on the cluster using vim:   
```
sbatch: error: Batch script contains DOS line breaks (\r\n)   
sbatch: error: instead of expected UNIX line breaks (\n).   
```  

#### <b>seg0_config.sh</b>     
<b>USER INPUT: update   
a) ```VERSION_DIR```:output folder on ```sandbox-cel``` scratch space or ```downspout-cel``` long-term storage          
b) ```END_YR```: prediction year  
c) ```VI_array```: list of VIs to use in (bash array form with spaces and parentheses) </b>   
* splits training digitizations -- field digitization polys and region chips --  by region into ```{VERSION_DIR}/user_train```   
* updates  ```{VERSION_DIR}/config_cultionet.yml ``` using seg0_config.sh settings         

#### <b>seg1_prepTrain_TS.sh</b>    
<b>d) USER INPUT: update #SBATCH --array GRID_ID to run 3k and 4k UNQ grid cells that have training digitizations  </b>                  
* for each UNQ GRID_ID that contains a 1km training chip, saves time-series in ```{VERSION_DIR}/time_series_vars/{REGION}``` -- clip to chip shape, named {REGION}, or clips and mosaics images where 1km chip region overlaps w/ more than one 20km x 20km processing GRID_ID cell        

#### <b>seg2_cnetTrain.sh</b>    
* saves list of regions that have completed time series as cnet_training_regions.txt, which is used by config_cultionet.yml in the following step   
* 'cultionet create' makes pytorch (.pt) training for each chip in ```{VERSION_DIR}/data/train/processed``` referencing config_cultionet.yml, ```{VERSION_DIR}/user_train``` chips & polys, and ```{VERSION_DIR}/time_series_vars``` veg indices  
* 'cultionet train' trains resunet model using training params from seg0_config.sh, saves model checkpoint in  ```ckpt```   

#### <b>seg3_cnetPredict.sh</b>     
<b>e) USER INPUT: update #SBATCH --array GRID_ID to run 3k and 4k UNQ grid cells to run inference on  </b>                 
* copies time-series for 20km x 20km UNQ GRID_ID cells into ```{VERSION_DIR}/time_series_vars/00{GRID_ID}/brdf_ts/ms/{VI}```       
* 'cultionet create-predict' saves pytorch prediction files for each 20km UNQ GRID_ID cell in #SBATCH --array in ```{VERSION_DIR}/data/predict/processed```   
* 'cultionet predict' runs inference on UNQ GRID_ID cells, save 4band predictions in ```{VERSION_DIR}/composites_probas``` where b1=crop extent probability, b2=distance to border, b3=border probability, and b4 is blank     

#### <b>sbatch seg4_fieldMetrics.sh</b>    
* saves five single-band raster features in ```{VERSION_DIR}/feats_{METHOD}_{CUTOFF}``` and vectors of field instances in  ```{VERSION_DIR}/infer_polys_{METHOD}_{CUTOFF}```    
* save single-band inference rasters -- 1:distance to border, 2:extent in ```{VERSION_DIR}/feats```    
* create vectors of crop field instances in  ```{VERSION_DIR}/infer_polys```. _merged.gpkg contains all grids and is used to calculate field size attributes -- 3:area, 4:area/perimeter(APR), 5:texture(seasonal stDev) -- then convert those attributes to rasters in ```{VERSION_DIR}/feats```
* Note: script doesn't append new grid cells onto _merged.gpkg, so if adding new grid cells, move or delete _merged.gpkg and rerun seg4_fieldMetrics.sh        

#### <b>sbatch seg5_chipAcc.sh</b>    
* calculate per-chip accuracy metrics compared to reference(training digitizations)       
* compare list of REF chips (currently uses training digitization chip regions not used in model training ```{VERSION_DIR}/cnet_training_regions_holdout.txt```  because time-series wasn't ready) vs PRED chips (inference-> instance vectors)   
    i. number of fields   
    ii. average field area   
    iii. total crop area   
