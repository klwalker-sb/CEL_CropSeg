import os
import rasterio as rio
import numpy as np
import geopandas as gpd
import pandas as pd
import geemap
import ee
from osgeo import gdal

ee.Initialize()
ee.Authenticate()


## MAPBIOMAS download

def MB_PRY_GEE(years, out_dir, grid_file):
    gdf = gpd.read_file(grid_file).to_crs('EPSG:4326')
    YR_names = ['classification_'+str(yr) for yr in years] 
    print(YR_names)
    for k, cell in gdf.iterrows():
        aoi = ee.Geometry.Rectangle([cell.geometry.bounds[0], cell.geometry.bounds[1], cell.geometry.bounds[2], cell.geometry.bounds[3]])
        UNQ = int(cell['UNQ'])

        dst = ee.Image( "projects/mapbiomas-public/assets/paraguay/collection1/mapbiomas_paraguay_collection1_integration_v1")
        bands = dst.select(YR_names)
        projection = bands.projection().getInfo() ## arbitrary band, to grab CRS extent info
        for year in YR_names: # save one band at a time 
            full_out_dir=os.path.join(out_dir, year.replace("classification", "MB_PRY"))
            if not os.path.exists(full_out_dir):
                os.makedirs(full_out_dir)
            out_name=os.path.join(full_out_dir, year.replace("classification", "MB_PRY")+"_"+"UNQ"+str(UNQ)+".tif")
            if os.path.exists(out_name):
                print(out_name+' exists')
            else:
                geemap.ee_export_image(bands.select(year), 
                                    filename=out_name, 
                                    crs=projection.get('crs'), crs_transform=projection.get('transform'),
                                    region=aoi, file_per_band=True)


from rasterio.warp import calculate_default_transform, transform, reproject, Resampling
from rasterio.merge import merge
from pathlib import Path
from rasterio.features import shapes

def mosaic_rasters(in_rasters, out_path):
    '''
    in_rasters: takes list of rasters to mosaic, or input directory where all files in that folder are mosaiced
    out_path: directory and name to save mosaic... no extension (will be .tif)
    returns out_path
    '''
    if type(in_rasters) == str:
        rasters = sorted([os.path.join(in_rasters, i) for i in os.listdir(in_rasters) if i.endswith(".tif")])
    elif type(in_rasters) == list:
        rasters = in_rasters
        
    with rio.open(rasters[1]) as src:
        tmp_arr = src.read()
        rast_crs=src.crs
        nodata = src.nodata
    # The merge function returns a single array and the affine transform info
    arr, out_trans = merge(rasters)

    out_meta = {'driver': 'GTiff', 'dtype':arr[0][0][0].dtype, 'nodata': nodata, 
    'count': arr.shape[0], 'height': arr.shape[1], 'width': arr.shape[2], 
    'crs': rast_crs, 'transform': out_trans}
    
    with rio.open(out_path, 'w', **out_meta) as dst:
        dst.write(arr)

    return out_path

from pathlib import Path
def make_reclass_dict(csv_path, old_col, new_col):
    '''
    0 stays as 0
    '''
    reclass_df = pd.read_csv(csv_path)
    old_new_dict = dict(zip(reclass_df[old_col], reclass_df[new_col]))
    old_new_dict[0] = 0   
    return old_new_dict

def reclassify_raster(raster_path, old_new, out_dir):
    '''
    in_dir = input directory of rasters to reclassify
    old_new = dictionary with old:new value as key:value pair. OR csv with 'old' column and 'new' column 
    out_dir = output directory to save reclassed raster, the name as the input raster+'_reclass'
    0 should be no data value 
    '''
    if type(old_new) == str:
        reclass_dict = make_reclass_dict(csv_path=old_new, old_col="old", new_col="new")
    elif type(old_new) == dict:
        reclass_dict = old_new
    print(reclass_dict)
    new_name = Path(raster_path).stem+"_reclass."+raster_path.split(".")[-1]
    with rio.open(raster_path) as src:
        old_arr = src.read(1)
        out_meta = src.meta.copy()
        if len(np.unique(old_arr)) > 1: ## if there are any values other than 0, nodata 
            new_arr = np.vectorize(reclass_dict.get)(old_arr)
            print(raster_path+ ": old raster vals: ", np.unique(old_arr), "    new raster vals: ", np.unique(new_arr))
            out_meta.update({'nodata': 0})
            with rio.open(os.path.join(out_dir, new_name), 'w', **out_meta) as dst:
                dst.write(new_arr, indexes=1)
            print(new_name)

