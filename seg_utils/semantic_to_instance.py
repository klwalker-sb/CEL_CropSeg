#!/usr/bin/ python

import os
import sys
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio.features import shapes
import geopandas as gpd
from osgeo import gdal
from scipy import ndimage as ndi
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from rasterstats import zonal_stats, point_query
import shapely
from shapely import BufferCapStyle, BufferJoinStyle   
from shapely.geometry import Point, LineString, Polygon
from numpy import copy
import gc
import math

import cnet_funcs as cf


#############################################################################################

from rasterio.features import shapes

def instance_to_poly(input_raster):
    with rio.open(input_raster, 'r') as tmp:
        rast = tmp.read(1)
        rast_crs = tmp.crs
    mask = None
    instance_shapes = ({'properties': {'raster_val': v}, 'geometry': s} for i, (s, v) in enumerate(shapes(rast, mask=mask, transform=tmp.transform)))
    #geoms = list(instance_shapes)
    vectorized_all  = gpd.GeoDataFrame.from_features(list(instance_shapes))
    vectorized = vectorized_all[vectorized_all['raster_val'] > 0.0] 
    # gdf = gpd.GeoDataFrame(pd.DataFrame(list(range(0,len(vectorized.geometry), 1)), columns=['pred_id']), 
    #                                  geometry=vectorized.geometry)
    vectorized['area'] = vectorized.area
    vectorized = vectorized[vectorized['area'] >= 900.0]

    vectorized = vectorized.set_crs(rast_crs)

    return vectorized

def cut_fields(vectorized_gdf):
    proj_crs = "EPSG:8858"
    vectorized_gdf['pred_id'] = list(range(0,len(vectorized_gdf), 1))

    ##  cut: negative buffer by X. if it's a polygon, rebuffer. if it's a multipolygon, split parts then rebuffer 
    eroded_geom = vectorized_gdf.buffer(distance=-10, resolution=1,  join_style=1)
    erd_clean = gpd.GeoDataFrame.from_features(eroded_geom.buffer(0))

    ## if it's an empty polygon (eroded away into nothing), take old geometry
    print(erd_clean)
    if not len(erd_clean) > 0:
        return erd_clean
    emptyTF = erd_clean[erd_clean['geometry'].isna()].reset_index()
    emptyTF.columns=['pred_id','empty']
    empty_old = vectorized_gdf.set_index('pred_id').join(emptyTF.set_index('pred_id'), how='inner')
    empty_old = empty_old[ empty_old['geometry'] !=  None]
    empty_old = empty_old.reset_index()
    empty_old = empty_old.drop(columns=['empty'])

    ## if it has a real geometry remaining but is a polygon or multipolygon 
    multi_polygons=[]
    polygons=[]
    not_empty = erd_clean[~erd_clean['geometry'].isna()].reset_index()
    for i, row in not_empty.iterrows():
        if row.geometry.geom_type.startswith("Multi"):
            multi_polygons.append(row.geometry)
        if row.geometry.geom_type.startswith("Polygon"):
            polygons.append(row.geometry)

    ## if it's a polygon (didn't cut), use old geom (orig shape) 
    polys_gdf = gpd.GeoDataFrame(gpd.geoseries.GeoSeries(polygons), 
                                 columns=['geometry'], 
                                 crs=proj_crs)
    old_polys = vectorized_gdf.sjoin(polys_gdf, how="inner", predicate="intersects")
    ## if it's a multipolygon, split parts (explode), then rebuffer to old geom 
    multi_geoS = gpd.geoseries.GeoSeries(multi_polygons).explode(index_parts=True)
    multi_geoS=multi_geoS.reset_index()
    multi_geoS=multi_geoS.drop(columns=["level_0", "level_1"])
    multi_explode = gpd.GeoDataFrame(geometry=multi_geoS[0])#
    multi_explode = multi_explode.set_crs(proj_crs)
    multi_explode_reBuff = multi_explode.buffer(10, join_style=1)
    multi_explode_reBuff = gpd.GeoDataFrame(geometry=multi_explode_reBuff)#

    ## combine 
    new_cut_geom = pd.concat([empty_old, old_polys, multi_explode_reBuff], axis=0)

    ## dissolve shapes that touch 
    print(len(new_cut_geom))
    dissolved_geom = gpd.geoseries.GeoSeries([geom for geom in new_cut_geom.unary_union.geoms])
    dissolved_gdf = gpd.GeoDataFrame(pd.DataFrame(list(range(0,len(dissolved_geom), 1)), columns=['pred_id']), geometry=dissolved_geom)    

    dissolved_gdf = dissolved_gdf.set_crs(proj_crs)
    
    return dissolved_gdf


def boundary_extent_thresh(bound_arr, ext_arr, bound_thresh, ext_thresh):
    
        ## THRESHOLD BOUNDARY MASK 
        bound_mask = np.copy(bound_arr).astype(np.uint8)
        bound_mask=np.where(bound_arr > bound_thresh*10000, 1, 0).astype(np.uint8)
        ## THRESHOLD EXTENT MASK # double mask extent w/ boundary mask
        extent_mask = np.copy(ext_arr).astype(np.uint8)
        extent_mask=np.where(ext_arr > ext_thresh*10000, 1, 0).astype(np.uint8)
        ## add boundary mask to crop mask (make boundary pixels 0, even if they're crop pixels)
        extent_mask=np.where(bound_mask == 1, 0, extent_mask).astype(np.uint8)
        
        return extent_mask
    
    
from scipy import ndimage as ndi
from skimage.segmentation import watershed
from skimage.feature import peak_local_max

def watershed_segmentation(dist_rast_masked, extent_mask, seed_size):
    ftp_xy = peak_local_max(dist_rast_masked,  
                            footprint=np.ones((int(seed_size), int(seed_size))),  
                            labels=extent_mask) 
    mask = np.zeros(extent_mask.shape, dtype=bool)
    mask[tuple(ftp_xy.T)] = True
    markers, _ = ndi.label(mask)
    instances = watershed(-dist_rast_masked,   
                          markers,  
                          mask=extent_mask) 
    return instances

def EO_instance(ext_arr, bound_arr, EO_thresh):
    
        extent = ext_arr/1000
        boundary=bound_arr/1000
        test_arr = 1 + extent - boundary
        out_arr = test_arr.copy()
        out_arr[out_arr < EO_thresh ] = 0
        out_arr[out_arr >= EO_thresh ] = 1
        
        return out_arr

    
def SINGLE_semantic2instance(pred_dir, out_dir, instance_method, bound_thresh=0.4, ext_thresh=0.6, seed_size=15, EO_thresh=7, singleBand=True):
    
    proc_grid = gpd.read_file('/home/downspout-cel/paraguay_lc/Segmentations/PY_grid_8858.gpkg')
    proc_grid = proc_grid.set_crs("EPSG:8858")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    files = []
    pred_rasts = sorted([os.path.join(pred_dir, i) for i in os.listdir(pred_dir) if i.endswith(".tif") ])
    for pred_rast in pred_rasts:
        grid = os.path.basename(pred_rast.split(".")[-2][-4:]) ## end file with grid number 
        bounds = proc_grid[proc_grid['UNQ'] == int(grid)].geometry.iloc[0].bounds ## bounds returns (minx, miny, maxx, maxy)
        boundary = (float(bounds[0]), float(bounds[2]), float(bounds[1]), float(bounds[3]))
        
        if singleBand==True:
            name = os.path.basename(pred_rast)            
            dist_pba_name = os.path.join(feat_dir, name.replace("pred_PY_", "pred_dst_"))
            extent_pba_name = os.path.join(feat_dir, name.replace("pred_PY_", "pred_ext_"))            
            with rio.open(pred_rast) as src:
                out_meta = src.meta.copy()
                dist_arr, bound_arr, ext_arr, _ = src.read()   
            if not os.path.exists(dist_pba_name):
                with rio.open(dist_pba_name, "w", **out_meta) as dst1:
                    dst1.write(dist_arr, indexes=1)
            if not os.path.exists(extent_pba_name):
                with rio.open(extent_pba_name, "w", **out_meta) as dst2:
                    dst2.write(ext_arr, indexes=1) 

        EO_name = os.path.join(out_dir, "PY_EO_"+str(grid)+"_"+str(EO_thresh).replace(".", "pt")+"th.tif")
        thresh_name = EO_name.replace("PY_EO_", "PY_thresh_").replace("_"+str(EO_thresh)+"th.tif", "_b"+str(bound_thresh)+"0_e"+str(ext_thresh)+"0")
        thresh_name=thresh_name.replace(".","pt",2)+".tif"
        water_name = thresh_name.replace("PY_thresh_", "PY_water_").replace(".tif", "_s"+str(seed_size)+".tif")
        if "EO" in instance_method:
            files.append(EO_name)
            fname = files[-1]
            print(fname)
        elif "thresh" in instance_method:
            files.append(thresh_name)
            fname = files[-1]
            print(fname)
        else:
            files.append(water_name)
            fname = files[-1]
            print(fname)
            
        if not os.path.exists(fname):
            with rio.open(pred_rast) as src:
                gt = src.transform
                offset = cf.windowed_read(gt, boundary)
                new_gt = rio.Affine(gt[0], gt[1], (gt[2] + (offset[0] * gt[0])), 0.0, gt[4], (gt[5] + (offset[1] * gt[4])))
                dist_arr, bound_arr, ext_arr, _ = src.read(window=Window(offset[0], offset[1], offset[2], offset[3]))      
                out_meta = src.meta.copy()
                ## read in the 2k x 2k grid shape window to remove cultionet inference edge-effects 
                out_meta.update({"count": 1, "dtype":np.int16, "transform":new_gt, "height":dist_arr.shape[0], "width":dist_arr.shape[1]})
                
         
        
                if "EO" in instance_method:
                    ## EO THRESHOLD METHOD (3)
                    EO_arr = EO_instance(ext_arr, bound_arr, EO_thresh)
                    ## SAVE SINGLE-BAND INSTANCE RASTER ** 3
                    with rio.open(EO_name, "w", **out_meta) as dst:
                        dst.write(EO_arr, indexes=1)         
                
                if "thresh" in instance_method  or "water" in instance_method:
                    
                    ## THRESHOLD BOUNDARY AND EXTENT RASTERS 
                    extent_mask = boundary_extent_thresh(bound_arr, ext_arr, bound_thresh, ext_thresh)

                    ## SAVE SINGLE-BAND INSTANCE RASTER only if it's not the watershed method 
                    if not "water" in instance_method: 
                        with rio.open(thresh_name, "w", **out_meta) as dst:
                            dst.write(extent_mask, indexes=1)     
                        
                if "water" in instance_method:
                    ## MASK DISTANCE RASTER
                    dist_rast_masked = np.copy(dist_arr)
                    dist_rast_masked = np.where(extent_mask == 0, 0, dist_rast_masked) 

                    ## WATERSHED SEGMENTATION 
                    instances = watershed_segmentation(dist_rast_masked, extent_mask, seed_size)

                    ## SAVE SINGLE-BAND INSTANCE RASTER ** 2
                    with rio.open(water_name, "w", **out_meta) as dst:
                        dst.write(instances, indexes=1)     


        ## instance to polys
        og_polys = instance_to_poly(fname)  
        if "water" in instance_method:
            fname = 'Wtrshd_pred_polys_b'+str(bound_thresh)[-1]+'0_e'+str(ext_thresh)[-1]+'0_s'+str(seed_size)+'_'+str(grid)+'.gpkg'
        elif "thresh" in instance_method:
            fname = instance_method+'_pred_polys_b'+str(bound_thresh)[-1]+'0_e'+str(ext_thresh)[-1]+'0_'+str(grid)+'.gpkg'
        elif "EO" in instance_method:
            fname = instance_method+'_pred_polys_'+str(EO_thresh).replace(".", "pt")+'th_'+str(grid)+'.gpkg'
        
        if not os.path.exists(os.path.join(out_dir, fname)):
            merged_polygons = og_polys.dissolve().explode(index_parts=True)
            merged_polygons.to_file(os.path.join(out_dir, fname), mode="w")

            ## cut fields 
            cut_polys = cut_fields(merged_polygons)
            print(cut_polys)
            if len(cut_polys) > 1:
                cut_polys.to_file(os.path.join(out_dir, fname.replace(".gpkg", "_cut.gpkg")), mode="w")

