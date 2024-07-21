#!/usr/bin/ python

import os, sys
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio.features import shapes
from rasterio import features
import geopandas as gpd
from rasterio.windows import Window
from shapely.geometry import Polygon
from rasterstats import zonal_stats, point_query

def img_to_bbox_offsets(gt, bbox):
    origin_x = gt[2]
    origin_y = gt[5]
    pixel_width = gt[0]
    pixel_height = gt[4]
    x1 = int(round((bbox[0] - origin_x) / pixel_width))
    x2 = int(round((bbox[1] - origin_x) / pixel_width))
    y1 = int(round((bbox[3] - origin_y) / pixel_height))
    y2 = int(round((bbox[2] - origin_y) / pixel_height))
    xsize = x2 - x1
    ysize = y2 - y1
    return [x1, y1, xsize, ysize]

def main():
    
    grid_num = str(sys.argv[1])
    grid_dir = sys.argv[2] ## "/home/downspout-cel/paraguay_lc/stac/grids/"
    shape_dir = sys.argv[3] ## "/home/downspout-cel/paraguay_lc/Segmentations/infer_polys_EO_7/"
    full_out_dir = sys.argv[4] ## "/home/downspout-cel/paraguay_lc/Segmentations/feats_EO_7/"
    stat = sys.argv[5] ## "std"
    jd_start = int(sys.argv[6]) ## 2021305
    jd_end = int(sys.argv[7]) ## 2021365

    grid_dir = os.path.join(grid_dir, "00"+grid_num, "brdf_ts", "ms", "gcvi")

    out_fn = os.path.join(full_out_dir, "AvgNovDec_FieldStd_"+grid_num+".tif")
    
    if not os.path.exists(out_fn):
        tmp_out_dir="/home/scratch-cel/tmp_rasts/"
        if not os.path.exists(tmp_out_dir):
            os.makedirs(tmp_out_dir)        
        
        proc_grid = gpd.read_file('/home/downspout-cel/paraguay_lc/Segmentations/PY_grid_8858.gpkg')
        proc_grid = proc_grid.set_crs("EPSG:8858")
        bounds = proc_grid[proc_grid['UNQ'] == int(grid_num)].geometry.iloc[0].bounds ## bounds returns (minx, miny, maxx, maxy)
        boundary = (float(bounds[0]), float(bounds[2]), float(bounds[1] ), float(bounds[3]))
        shape = gpd.read_file([os.path.join(shape_dir,i) for i in os.listdir(shape_dir) if grid_num in i and i.endswith(".gpkg")][0])
        
        rasts = sorted([i for i in os.listdir(grid_dir) if i.endswith(".tif") and (int(i.replace(".tif", "")) > jd_start and int(i.replace(".tif", "")) < jd_end)])
        stack = []
        for rast in rasts:
            with rio.open(os.path.join(grid_dir, rast)) as src:
                gt = src.transform
                offset = img_to_bbox_offsets(gt, boundary)
                new_gt = rio.Affine(gt[0], gt[1], (gt[2] + (offset[0] * gt[0])), 0.0, gt[4], (gt[5] + (offset[1] * gt[4])))
                arr = src.read(window=Window(offset[0], offset[1], offset[2], offset[3]))      
                stack.append(arr)            
                out_meta = src.meta.copy()
                out_meta.update({"count": 1, "dtype":np.int16, "transform":new_gt, "width":2000, "height":2000})
        avg_arr = np.nanmean(stack, axis=0)
        out_shape = avg_arr.shape
        ## save intermediate mean raster 
        out_name = os.path.join(tmp_out_dir, "NovDecMean_"+grid_num+".tif")
        with rio.open(out_name, "w", **out_meta) as dst:
            dst.write(avg_arr)

        ## within each polygon, find st dev of Nov-Dec mean
        gdf = shape.join(pd.DataFrame(zonal_stats(
            vectors=shape['geometry'], raster=out_name, stats=[stat])), how='left' )
        ## delete intermediate mean raster
        os.remove(out_name)
        #os.remove(out_name.replace(".tif", ".tif.aux.xml"))

        ## save raster 
        with rio.open(out_fn, 'w+', **out_meta) as dst:
            tmp_arr = dst.read(1)
            ## rasterize polygon using st dev value
            shapes = ((geom,value) for geom, value in zip(gdf.geometry, gdf[stat]))
            image = features.rasterize( ((g, v) for g, v in shapes), out_shape=out_shape[1:], transform=new_gt)
            dst.write_band(1, image)
            print(out_fn)
        
if __name__ == "__main__":
    main()