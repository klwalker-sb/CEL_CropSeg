#!/usr/bin/ python

import os, sys
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio.features import shapes
from rasterio import features
import geopandas as gpd

import cnet_funcs as cf
imoprt semantic_to_instance as s2i


def main():

    instance_method = sys.argv[1] 
    thresholds = sys.argv[2] 
    version_dir = sys.argv[3] 
    grid_file = sys.argv[4] 
    pred_prefix = sys.argv[5]
    
    thresh_list = thresholds.split(",")
    params = '_'.join(thresh_list).replace(".", "pt", 3)

    pred_dir = os.path.join(version_dir, "composites_probas")
    out_dir = os.path.join(version_dir, "_".join(["infer_polys",str(instance_method),params]))
    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    feat_dir = os.path.join(version_dir, "_".join(["feats",str(instance_method),params]))
    if not os.path.exists(feat_dir):
        os.makedirs(feat_dir)    

    if len(thresh_list) == 1:
        if len(thresh_list[0]) > 1:
            EOt = np.float32(thresh_list[0])
        elif len(thresh_list[0]) == 1:
            EOt = int(thresh_list[0])
            
        s2i.SINGLE_semantic2instance(pred_dir, out_dir, instance_method, EO_thresh=EOt, singleBand=True)
    elif len(thresh_list) == 2:
        s2i.SINGLE_semantic2instance(pred_dir, out_dir, instance_method, bound_thresh=np.float32(thresh_list[0]), ext_thresh=np.float32(thresh_list[1]), singleBand=True)
    elif len(thresh_list) == 3:
        s2i.SINGLE_semantic2instance(pred_dir, out_dir, instance_method, bound_thresh=np.float32(thresh_list[0]), ext_thresh=np.float32(thresh_list[1]), seed_size=int(thresh_list[2]), singleBand=True)
    ## save extent band and distance to boundary band. also write instance raster -> polys + cut



    proc_grid = gpd.read_file(grid_file)
    proj_crs = proc_grid.crs
    ## merge polys so area calculations aren't cut off at edges
    in_dir = out_dir

    merged_fi = os.path.join(out_dir, str(instance_method)+"_"+params+"_merged.gpkg")
    if not os.path.exists(merged_fi):
        files = sorted([os.path.join(in_dir, fi) for fi in os.listdir(in_dir) if fi.endswith("_cut.gpkg") ])
        print(files)
        gdfs = [gpd.read_file(f) for f in files]
        field_shp = gpd.GeoDataFrame(pd.concat(gdfs, ignore_index=True)).dissolve().explode()
        
        ## add field size attributes 
        field_shp['area'] = field_shp.area*0.0001
        field_shp['perimeter'] = field_shp.length
        field_shp['APR'] = field_shp.area/field_shp.length
        
        ## delete fields < 30m x 30m
        field_shp = field_shp[field_shp.area >= 900.0]        

        field_shp = field_shp.set_crs(proj_crs)
        field_shp.to_file(merged_fi, mode="w")
    else:
        ## save single merged gpkg to file for calculating stats (field size stats per admin area) from vectors 
        field_shp = gpd.read_file(merged_fi)

    ## write grid cell per file based on grid shape

    files = sorted([os.path.join(in_dir, fi) for fi in os.listdir(in_dir) if fi.endswith("_cut.gpkg") ])
    grids = [os.path.basename(i).replace("_cut.gpkg", "")[-4:] for i in files]
    for grid in grids:
        grid_bound = proc_grid[proc_grid['UNQ'] == int(grid)].geometry.iloc[0]
        polys_per_grid = gpd.clip(field_shp, grid_bound) ## making area raster from merged shape 
        rst_fn = os.path.join(out_dir, "_".join([pred_prefix, str(instance_method), str(grid), params+"th.tif"]))

        ## raster to use as template
        rst = rio.open(rst_fn)
        meta = rst.meta.copy()
        meta.update({"dtype":np.float64})
        
        for attrib in ["area", "APR"]:
            out_fn = os.path.join(feat_dir, 
                                  "pred_"+attrib+"_"+str(grid)+".tif")
            with rio.open(out_fn, 'w+', **meta) as src:
                tmp_arr = src.read(1)
                # this is where we create a generator of geom, value pairs to use in rasterizing
                shapes = ((geom,value) for geom, value in zip(polys_per_grid.geometry, polys_per_grid[attrib]))
                image = features.rasterize(((g, v) for g, v in shapes), out_shape=src.shape, transform=src.transform)
                src.write_band(1, image)
        
        

if __name__ == "__main__":
    main()
