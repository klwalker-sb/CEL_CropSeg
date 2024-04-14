#!/usr/bin/ python


def main():

    import os, sys
    import shutil
    import pandas as pd
    
    import cnet_funcs as cf
    
    VERSION_DIR = sys.argv[1]
    END_YR=sys.argv[2]
    TRAINING_POLYS = sys.argv[3]
    VIs=sys.argv[4]
    local_path - "~/code/bash" ##os.path.join( __file__.replace(os.path.basename( __file__), ""), "cultionetTEMP")
    
    ## 0) do in template folder once, then skip once its filled out and copy files into new version directory where testing of bands or new years are done
    user_train_dir =  os.path.join(local_path, "user_train")
    if not os.path.exists(user_train_dir):
        os.makedirs(user_train_dir)
    if not os.path.exists(os.path.join(local_path, "time_series_vars")):
        os.makedirs(os.path.join(local_path, "time_series_vars"))   
    if not os.path.exists(os.path.join(local_path, "data")):
        os.makedirs(os.path.join(local_path, "data"))        
    if len(os.listdir(user_train_dir)) < 1:
        ## 1. PREP USER_TRAIN: create user_train "region_grid_year" and "region_poly_year" .gpkg's
        regions_fi = cf.prep_user_train(training_digitizations=TRAINING_POLYS, user_train_dir=user_train_dir, end_yr=END_YR)
    else:
        print('not overwriting user_train files')

    ## 2) copy template folder with user_train to create .pt training files into that version directory
    if not os.path.exists(VERSION_DIR):
        destination = shutil.copytree(local_path, VERSION_DIR)  
    

    ## 3) fill out config file based on project params
    config_file = os.path.join(VERSION_DIR, "config_cultionet.yml")
    
    yml_params={"image_vis":VIs[1:-1].split(","), "regions": "!!null", 
                "region_id_file":os.path.join(VERSION_DIR, "cnet_training_regions.txt"), 
                "years":[int(END_YR)],   "start_year":int(END_YR)-1,  "predict_year":int(END_YR )}
                     
    cf.update_yml(config_file, yml_params)


if __name__ == "__main__":
    main()
