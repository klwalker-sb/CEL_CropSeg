#!/usr/bin/ python

import os, sys
import json
import pandas as pd
import geopandas as gpd
import numpy as np
from pathlib import Path
import shutil
from shutil import copyfile
import rasterio as rio
from rasterio.windows import Window
from rasterio.features import shapes, coords
from rasterio.warp import calculate_default_transform, reproject, Resampling
from shapely.geometry import box, Polygon
from datetime import datetime



import yaml


def update_yml(yml_path, param_value_dict):
    with open(yml_path, 'r') as file:
        value = yaml.safe_load(file)
    for key in param_value_dict:
        value[key] = param_value_dict[key]
    
    with open(yml_path, 'w') as file:
        yaml.dump(value, file, sort_keys=False)        



###############################################


def prep_user_train(training_digitizations, user_train_dir, end_yr):
    class_col = "class"


    polys = gpd.read_file(training_digitizations, mode="r")
    chips = gpd.read_file(training_digitizations.replace("_Polys", "_Chips"),  mode="r")
    proj_crs = polys.crs
    polys = polys[polys.columns.drop(list(polys.filter(regex='Notes')))]
    chips = chips[chips.columns.drop(list(chips.filter(regex='Notes')))]
    
    ## CHIPS 
    for kk, chp in sorted(chips.iterrows()):
        chip_region = chp.region
        out_chip_name = os.path.join(user_train_dir, str(chip_region)+"_grid_"+str(end_yr)+".gpkg")   
        if not os.path.exists(out_chip_name): ###############
            df = chp.rename(None).to_frame().T ## format chip dataframe 
            chip_gdf = gpd.GeoDataFrame(df, crs=proj_crs, geometry=df.geometry)  ## create chip's GeoDataFrame
            chip_gdf.to_file(out_chip_name, crs=proj_crs, driver="GPKG") ### output chip 
            chip_polys = polys.sjoin(chip_gdf, how="inner") ## select digitizations that intersect chip  
            chip_polys = chip_polys[chip_polys.columns.drop(list(chip_polys.filter(regex='right')))] ## drop duplicate columns
            chip_polys = chip_polys[chip_polys.columns.drop(list(chip_polys.filter(regex='left')))] ## drop duplicate columns
            chip_polys['Name'] = str(chip_region)+"_poly_"+str(end_yr) ## Name column for cultionet 
            chip_polys['region'] = str(chip_region) ## region column for cultionet 
            chip_polys['class'] = chip_polys[class_col]
            if len(chip_polys['class'].unique()) == 1 and 0 in chip_polys['class'].unique(): ## if there are only non-crop digitizations (based on recoded 'class')
                chip_polys = chip_polys.drop(chip_polys.index[1:]) ## delete all rows after the first 
                new_geom = chip_gdf.geometry.buffer(50) ## copy the chip's geometry and buffer by 50m               
                chip_polys['geometry'] = new_geom.iloc[0] ## assign new buffered geometry ### MAYBE RM ILOC[0]??

            else:
                geom_tmp = chip_polys.geometry.buffer(-0.000001) ## using buffered 'geom' removes the Z dimension 
                geom = geom_tmp.buffer(+0.000001) ## using buffered 'geom' removes the Z dimension 
                chip_polys = gpd.GeoDataFrame(chip_polys, crs=proj_crs, geometry=geom) ## create field digitization's GeoDataFrame
            chip_polys = chip_polys[['class', 'region', 'Name', 'geometry']]
            print(chip_polys)
            out_polys_name = os.path.join(user_train_dir, str(chip_region)+"_poly_"+str(end_yr)+".gpkg")
            chip_polys.to_file(out_polys_name,  crs=proj_crs, driver="GPKG", mode="w") ## , layer=str(chip_region) ## export digitization polys             

        else:
            print('user_train already made for '+str(out_chip_name))


###############################################

def clip_chip(grid_num, spec_index, project_directory, version_dir, grid_file, end_yr):
    names = [i.replace("_poly_"+str(end_yr)+".gpkg", "") for i in os.listdir(os.path.join(version_dir, "user_train")) if ("_grid_" not in i and i.startswith(grid_num))] 
    print(names)
    chip_list = [str(i)+"_grid_"+str(end_yr)+".gpkg" for i in names]
    for chip in chip_list:
        chip_num = int(chip.split("_")[0])
        chip_clip_shape = gpd.read_file(os.path.join(version_dir, "user_train", chip))
        bounds = (float(chip_clip_shape.bounds['minx']), float(chip_clip_shape.bounds['maxx']), float(chip_clip_shape.bounds['miny'] ), float(chip_clip_shape.bounds['maxy']))
        rast_dir=os.path.join(project_directory,  str(grid_num).zfill(6), "brdf_ts", "ms", spec_index)
        print(rast_dir)
        

        if os.path.exists(rast_dir):
            
            if "LUCinLA" in grid_file:
                month_day = "06-01"
            elif "AI4B" in grid_file:
                month_day = "01-01"
                
            ## check that the VI folder was made after 7/15/2023 
            dd_made, mm_made, yyyy_made = datetime.fromtimestamp(os.path.getctime(rast_dir)).strftime("%d-%m-%Y").split("-")
            if (int(yyyy_made)>2023) or (int(yyyy_made)==2023 and int(mm_made) >=7) or "AI4Boundaries" not in project_directory: ##or  (int(yyyy_made)==2023 and int(mm_made) == 7 and int(dd_made) > 15)
                rast_list = file_to_copy(ImgDir=rast_dir, EndYr=end_yr, MMDD=month_day) ###### LIST OF FILES ## ENTER START YEAR AND START DATE

                for rast in sorted(rast_list):
                    with rio.open(rast, 'r') as src:
                        grid_gt = src.transform
                        # find XY offsets locating where chip is within grid image (from chip-grid offsets and chip boundary size)
                        src_offset = windowed_read(grid_gt, bounds)
                        # read in only that window
                        clipped_rast = src.read(1, window=Window(src_offset[0], src_offset[1], src_offset[2], src_offset[3]))
                        out_dirF = Path(os.path.join(version_dir, "time_series_vars", str(chip_num).zfill(6), "brdf_ts", "ms", str(spec_index)))
                        out_dirF.mkdir(parents=True,exist_ok=True)
                        out_rast = os.path.join(out_dirF, rast.split("/")[-1] )   
                        print(out_rast)
                        if not os.path.exists(out_rast):
                            if clipped_rast.shape == (100, 100):
                                new_gt = rio.Affine(grid_gt[0], grid_gt[1], (grid_gt[2] + (src_offset[0] * grid_gt[0])), 0.0, grid_gt[4], (grid_gt[5] + (src_offset[1] * grid_gt[4])))
                                with rio.open(out_rast, "w",  driver='GTiff', width=clipped_rast.shape[1], height=clipped_rast.shape[0], count=1,  dtype=np.int16, crs=src.crs, transform=new_gt) as dst:
                                    dst.write(clipped_rast, 1)
                            else:
                                # load grid shape to find grids that intersect with chip shape 
                                grids = gpd.read_file(grid_file)

                                chip_within_grids = gpd.sjoin(grids, chip_clip_shape, op='intersects') 
                                both_grids = chip_within_grids.UNQ.to_list()
                                print(both_grids)
                                grid_folder1 = os.path.join(project_directory, str(both_grids[0]).zfill(6),"brdf_ts", "ms", str(spec_index))
                                raster1 = os.path.join(grid_folder1, rast.split("/")[-1])                            
                                if len(both_grids) == 2:
                                    grid_folder2 = os.path.join(project_directory, str(both_grids[1]).zfill(6),"brdf_ts", "ms", str(spec_index)) 
                                    raster2 = os.path.join(grid_folder2, rast.split("/")[-1])
                                    mosaic_list = [raster1, raster2]
                                else:
                                    mosaic_list = [raster1]

                                grid_mosaic=os.path.join(out_dirF, "tmp_mos_"+str(rast.split("/")[-1])+".vrt")
                                gdal.BuildVRT(grid_mosaic, mosaic_list)
                                # read in window of chip bounds 
                                with rio.open(grid_mosaic) as src2:
                                    grid_gt2 = src2.transform

                                    src2_offset = windowed_read(grid_gt2, bounds)
                                    clipped_rast2 = src2.read(1, window=Window(src2_offset[0], src2_offset[1], src2_offset[2], src2_offset[3]))
                                    new_gt2 = rio.Affine(grid_gt2[0], grid_gt2[1], (grid_gt2[2] + (src2_offset[0] * grid_gt2[0])), 0.0, grid_gt2[4], (grid_gt2[5] + (src2_offset[1] * grid_gt2[4])))
                                    with rio.open(out_rast, "w",  driver='GTiff', width=clipped_rast2.shape[1], height=clipped_rast2.shape[0], count=1,  dtype=np.int16, crs=src2.crs, transform=new_gt2) as dst:
                                        dst.write(clipped_rast2, 1)     
                                # delete tmp mosaic 
                                os.remove(grid_mosaic)
                        else:
                            print('mosaic made: '+str(out_dirF))
                        print(out_dirF)
            else:
                print('old folder: '+rast_dir)
                
                
def windowed_read(gt, bbox): 
    """
    helper function for rasterio windowed reading of chip within grid to save into cnet time_series_vars folder
    gt = main raster's geotransformation (src.transform)
    bbox = bounding box polygon as subset from raster to read in
    """
    origin_x = gt[2]
    origin_y = gt[5]
    pixel_width = gt[0]
    pixel_height = gt[4]
    x1_window_offset = int(round((bbox[0] - origin_x) / pixel_width))
    x2_window_offset = int(round((bbox[1] - origin_x) / pixel_width))
    y1_window_offset = int(round((bbox[3] - origin_y) / pixel_height))
    y2_window_offset = int(round((bbox[2] - origin_y) / pixel_height))
    x_window_size = x2_window_offset - x1_window_offset
    y_window_size = y2_window_offset - y1_window_offset
    return [x1_window_offset, y1_window_offset, x_window_size, y_window_size]

###############################################


def ready_regions(version_dir, vi_list=["evi2", "gcvi", "wi"]):
    if type(vi_list)==str:
        vi_list = vi_list[1:-2].split(",")
    
    time_series_dir = os.path.join(version_dir, "time_series_vars")
    user_train_regions = os.listdir(time_series_dir)
    not_ready = []
    for rgn in user_train_regions:
        region_folder = os.path.join(time_series_dir, str(rgn))
        vis = os.listdir(os.path.join(region_folder, 'brdf_ts', 'ms'))
        for vi in vi_list:
            if vi not in vis:
                not_ready.append(str(rgn)+"_"+str(vi))
             #   print(str(rgn)+' missing ' + str(vi))
            elif vi in vis:
                num_tifs = [i for i in os.listdir(os.path.join(region_folder, 'brdf_ts', 'ms', str(vi))) if i.endswith(".tif")]
                if len(num_tifs) != 13:
                 #   print(str(rgn)+' does not have 13 images of ' + str(vi))
                    not_ready.append(str(rgn)+"_"+str(vi))
                 #   print(rgn)
    regions_not_ready = list(set([i for i in not_ready]))
    ready = sorted([i for i in user_train_regions if i not in regions_not_ready])
    config_file = os.path.join(version_dir, "config_cultionet.yml")
    ## save file for user_train_regions that are ready (for the config file)
    chip_file = os.path.join(version_dir, "cnet_training_regions.txt")
    txt = open(chip_file, 'w')
                               
    txt.write("id"+"\n")     
    for rdy in ready:
        if not rdy.startswith("."):
            txt.write(rdy+"\n")       
    txt.close()



###############################################

def file_to_copy(ImgDir, EndYr, MMDD):
    StartYr = EndYr - 1
    ts = pd.Timestamp(year=StartYr,  month=int(MMDD[:2]),   day=int(MMDD[-2:])) 
    start_jd = ts.timetuple().tm_yday
    ## all images in grid/brdf_ts/ms/VI folder that start with the StartYr or EndYr (i.e. 2020 or 2021)
    all_images = [i for i in sorted(os.listdir(ImgDir)) if (i.startswith(str(StartYr)) | i.startswith(str(EndYr)))]
    ## subset from all_images where the julian date is greater than or equal to the MMDD julian date in the StartYr and less than or equal to the julian date in EndYr
    imgs2copy = [os.path.join(ImgDir, img) for img in all_images if ((int(img[:4]) == StartYr and int(img[4:7]) >= int(start_jd)) | (int(img[:4]) == EndYr and int(img[4:7]) <= int(start_jd)))]
    ## take every third image [start:stop:step] in time series
    copy_images = imgs2copy[::3]
    return copy_images


## for before predict bash script
def copy_pred_grid(grid, spec_index, proj_stac_dir, version_dir, mmdd, end_yr):

    in_dir = os.path.join(proj_stac_dir, str(grid).zfill(6), "brdf_ts", "ms", str(spec_index))
    if not os.path.exists(in_dir):
        print(grid, 'missing time series for ', str(spec_index))
    else:
        ## check that the VI folder was made after 7/15/2023 
        dd_made, mm_made, yyyy_made = datetime.fromtimestamp(os.path.getctime(in_dir)).strftime("%d-%m-%Y").split("-")
       ### if (int(yyyy_made)>2023) or (int(yyyy_made)==2023 and int(mm_made) >=7) or "AI4Boundaries" not in proj_stac_dir : ##or  (int(yyyy_made)==2023 and int(mm_made) == 7 and int(dd_made) > 15)
        out_dir = os.path.join(str(version_dir), "time_series_vars", str(grid).zfill(6), "brdf_ts", "ms", str(spec_index))

        ## check that there are 13 files to move 
        move = file_to_copy(ImgDir=in_dir, EndYr=end_yr, MMDD=mmdd)
        if len(move) != 13:
            print('there should be 13 time series images to move in '+in_dir)

        if not os.path.exists(out_dir):
            os.makedirs(out_dir)
            for fi in move:
                out_fi = os.path.join(out_dir, fi.split("/")[-1])
                if not os.path.exists(out_fi):
                    copyfile(fi, out_fi)   

        elif os.path.exists(out_dir):
            if sorted(os.listdir(out_dir)) == sorted([i.split("/")[-1] for i in move]):
              #  print('grid time series images already moved into '+str(out_dir))
                pass
            elif len(os.listdir(out_dir)) == 0:
                for fi in move:
                    out_fi = os.path.join(out_dir, fi.split("/")[-1])
                    if not os.path.exists(out_fi):
                        copyfile(fi, out_fi)         
            else:
                print(str(out_dir)+' made but not all files are in there')
    # else:
    #     print('old folder: '+in_dir)



###############################################

