#!/usr/bin/ python

import os
import sys
import pandas as pd
import numpy as np
import rasterio as rio
from rasterio.features import shapes
import geopandas as gpd
from scipy import ndimage as ndi
from skimage.segmentation import watershed
from skimage.feature import peak_local_max
from rasterstats import zonal_stats, point_query
from shapely.geometry import Point, LineString, Polygon
from numpy import copy
import math

import cnet_funcs as cf

def chip_acc(predPoly_dir, pred_prefix, RefShp, class_col="class", crop_classes=[1]):
    print(predPoly_dir)
    
    RefPolys = gpd.read_file(RefShp) ## pred vector file 
    regions = sorted(RefPolys['region'].to_list())
    chips_wCrops=[]
    chips_noCrops=[]
    for Region in sorted(list(set(regions))):
        RefPoly_gdf = RefPolys[RefPolys["region"]==int(Region)] 
        RefPoly_gdf = RefPoly_gdf[RefPoly_gdf[class_col].isin(crop_classes)]
        if len(RefPoly_gdf) >= 1:
            chips_wCrops.append(Region)
        else:
            chips_noCrops.append(Region)

    chip_df = gpd.read_file(RefShp.replace("_Polys_", "_Chips_"))
    chip_df['region'] = [int(i) for i in chip_df['region']]
    RefPolys['region'] = [int(i) for i in RefPolys['region']]
    RefPolys['UNQ'] = [int(str(i)[:4]) for i in RefPolys['region']]

    all_chips_wCrops=[]
    for Region in sorted(chips_wCrops): ## subset for quick testing
        PredVector = os.path.join(predPoly_dir, pred_prefix+'_'+str(Region)[:4]+"_cut.gpkg")
        if os.path.exists(PredVector):
            PredPolys = gpd.read_file(PredVector)
            chip_shape = chip_df[chip_df["region"]==int(Region)] 
            RefPoly_gdf = RefPolys[RefPolys["region"]==int(Region)] 
            RefPoly_gdf = RefPoly_gdf[RefPoly_gdf[class_col].isin(crop_classes)]
            RefPoly_gdf = gpd.clip(RefPoly_gdf, chip_shape)

            PredPoly_gdf = PredPolys.sjoin(chip_shape, how="inner")
            PredPoly_gdf = gpd.clip(PredPoly_gdf, chip_shape)

            if len(PredPoly_gdf) == 0: ## underpredicting where pred = 0 and ref > 0
                all_chips_wCrops.append([int(Region), pred_prefix, len(RefPoly_gdf)*-1,  np.nanmean(RefPoly_gdf.area)*-1, np.sum(RefPoly_gdf.area)*-1 ])
            else: 
                if len(PredPoly_gdf) > len(RefPoly_gdf):
                    all_chips_wCrops.append([Region, pred_prefix, (len(PredPoly_gdf)/len(RefPoly_gdf))-1 ])
                else:
                    all_chips_wCrops.append([Region, pred_prefix, 1-(len(RefPoly_gdf)/len(PredPoly_gdf))])            
                if np.nanmean(PredPoly_gdf.area) > np.nanmean(RefPoly_gdf.area):
                    all_chips_wCrops[-1].append((np.nanmean(PredPoly_gdf.area)/np.nanmean(RefPoly_gdf.area))-1 )
                else:
                    all_chips_wCrops[-1].append(1-(np.nanmean(RefPoly_gdf.area)/np.nanmean(PredPoly_gdf.area)) )
                if np.sum(PredPoly_gdf.area) > np.sum(RefPoly_gdf.area):
                    all_chips_wCrops[-1].append((np.sum(PredPoly_gdf.area)/np.sum(RefPoly_gdf.area))-1 )
                else:
                    all_chips_wCrops[-1].append(1- (np.sum(RefPoly_gdf.area)/np.sum(PredPoly_gdf.area)) )
                    
            all_chips_wCrops[-1] = [0 if i==-np.inf else i for i in all_chips_wCrops[-1]]
            print(all_chips_wCrops[-1])

    all_chips_noCrops=[]
    for Region in sorted(chips_noCrops): ## subset for quick testing
        PredVector = os.path.join(predPoly_dir, pred_prefix+'_'+str(Region)[:4]+"_cut.gpkg")
        if os.path.exists(PredVector):
            PredPolys = gpd.read_file(PredVector)

            chip_shape = chip_df[chip_df["region"]==int(Region)] 
            RefPoly_gdf = RefPolys[RefPolys["region"]==int(Region)] 
            RefPoly_gdf = RefPoly_gdf[RefPoly_gdf[class_col].isin(crop_classes)]
            RefPoly_gdf = gpd.clip(RefPoly_gdf, chip_shape)
            PredPoly_gdf = PredPolys.sjoin(chip_shape, how="inner")
            PredPoly_gdf = gpd.clip(PredPoly_gdf, chip_shape)

            if len(PredPoly_gdf)==0:
                all_chips_noCrops.append([str(Region), pred_prefix, 0, 0, 0])
            else: ## if pred > 0 and ref = 0 (overpredict)
                all_chips_noCrops.append([str(Region), pred_prefix, len(PredPoly_gdf), np.nanmean(PredPoly_gdf.area), np.sum(PredPoly_gdf.area)  ])        
                
            all_chips_noCrops[-1] = [0 if i==-np.inf else i for i in all_chips_noCrops[-1]]
            print(all_chips_noCrops[-1])

    wCrops_df = pd.DataFrame(all_chips_wCrops, columns=["region", "version", "numFields", "avgArea", "totalCropArea"])
    noCrops_df = pd.DataFrame(all_chips_noCrops, columns=["region", "version", "numFields", "avgArea", "totalCropArea"])
    all_chips_df = pd.concat([wCrops_df, noCrops_df])
    
    NovSampCells=pd.read_csv("/home/downspout-cel/paraguay_lc/Segmentations/NovSampCells.csv")
    keep_grids = sorted(NovSampCells['id'].to_list())
    done_regions = [i for i in all_chips_df['region']]
    keep_regions = [i for i in done_regions if int(str(i)[:4]) in keep_grids]   
    wCrops_df=wCrops_df[wCrops_df['region'].isin(keep_regions)]
    noCrops_df=noCrops_df[noCrops_df['region'].isin(keep_regions)]    

    wCrops_df['version'] = [i+"_wCrops" for i in wCrops_df['version']]
    noCrops_df['version'] = [i+"_noCrops" for i in noCrops_df['version']]    
    
    all_chips_df = pd.concat([wCrops_df, noCrops_df])
    out_name = os.path.join("/home/l_sharwood/code/cnet_scripts/accuracy/", "chip_acc_"+pred_prefix+"_allRegions_"+str(len(all_chips_df))+".csv")
    all_chips_df.to_csv(out_name)
    
    wCrop_grouped = wCrops_df.groupby(["version"])[["numFields", "avgArea", "totalCropArea"]].mean()
    noCrop_grouped = noCrops_df.groupby(["version"])[["numFields", "avgArea", "totalCropArea"]].mean()
    all_grouped = pd.concat([wCrop_grouped, noCrop_grouped])
    all_grouped.to_csv(out_name.replace("_allRegions_"+str(len(all_chips_df))+".csv", "_avg.csv"))
    
    return all_chips_df, all_grouped

#####################################
## field accuracy metrics (IoU)

def largest_overlap(ref_df, pred_df):        
    ## find all Pred fields that intersect (spatial join), as a list (1:many)
    intersecting = pd.DataFrame(pred_df.sjoin(ref_df, how='inner')['Rindex']) #Find the polygons that intersect. Keep savedindex as a series
    pred_val_matches = intersecting.reset_index()
    pred_val_matches.columns = ["PredIndex", "RefIndex"]
    pred_ref_intersecting_index = pd.DataFrame(pred_val_matches.groupby(['RefIndex'])['PredIndex'].apply(list)).reset_index()

    ## find the polygon w/ largest overlap w/ each Ref field (1:1)
    overlap_areas_all_fields=[]
    for k,v in pred_ref_intersecting_index.iterrows():
        ref_index = v[0]
        pred_matches = v[1]
        Rdf=ref_df[ref_df["Rindex"]==ref_index]
        overlap_areas_per_ref_field=[]
        pred_indices_per_ref_field=[]
        for pred_index in pred_matches:
            Pdf = pred_df[pred_df["Pindex"]==pred_index]
            Rdf['area'] = Rdf.geometry.area
            Pdf['area'] = Pdf.geometry.area 
            intersect_df = gpd.overlay(Rdf, Pdf, how="intersection")
            if not len(intersect_df) == 0:
                interction_area = intersect_df['geometry'].area
                pred_indices_per_ref_field.append(pred_index)
                overlap_areas_per_ref_field.append(interction_area[0])
            else: ################################************************ append something else here to signify no match
                pred_indices_per_ref_field.append(0)
                overlap_areas_per_ref_field.append(0)                
        overlap_areas_all_fields.append(dict(zip(pred_indices_per_ref_field, overlap_areas_per_ref_field)))

    ## find largest overlap from list 
    largest_overlapping_pred = []
    for r in overlap_areas_all_fields:
        max_index = max(r, key=r.get)
        largest_overlapping_pred.append(max_index)
    RP_index_matches = list(zip(pred_ref_intersecting_index['RefIndex'].to_list(), largest_overlapping_pred))
    return RP_index_matches
 
def calc_metrics(PredVector, ref_df, pred_df, RP_index_matches):
    IoUs=[]
    overSeg_rates=[]
    underSeg_rates=[]
    location_similarities=[]

    for i in RP_index_matches:
        ref_gdf = ref_df[ref_df['Rindex'] == i[0]]
        pred_gdf = pred_df[pred_df['Pindex'] == i[1]]
        intersect_df = gpd.overlay(ref_gdf, pred_gdf, how="intersection")
        ref_area = ref_gdf['geometry'].iloc[0].area
        pred_area = pred_gdf['geometry'].iloc[0].area    
        intersect_area = intersect_df['geometry'].loc[0].area
        union_area = ref_area+pred_area-intersect_area

        ## IoU
        IoUs.append(intersect_area/union_area)
        ## overseg rates 
        overSeg_rates.append(1-(intersect_area/ref_area))

        ## underseg rates 
        underSeg_rates.append(1-(intersect_area/pred_area))    

        ## location similarity 
        pred_centroid = pred_gdf.geometry.centroid.iloc[0]
        ref_centroid = ref_gdf.geometry.centroid.iloc[0]
        centr_dist=ref_centroid.distance(pred_centroid) 
        circRadius=2*np.sqrt(union_area/np.pi)
        location_similarities.append(1-centr_dist/circRadius)

    filename = os.path.basename(PredVector)
    Region = (list(set(ref_df['region'])))[0] ### UNQ or region
    print(Region)
    match_metrics = [os.path.basename(filename), Region, RP_index_matches,IoUs,overSeg_rates,underSeg_rates,location_similarities]
    match_metrics=pd.DataFrame(match_metrics).T
    
    ## show accuracy metrics by chip 
    match_metrics_per_grid = [os.path.basename(filename), Region, np.mean(IoUs), np.mean(overSeg_rates), np.mean(underSeg_rates), np.mean(location_similarities)]
    metrics_per_grid = pd.DataFrame(match_metrics_per_grid).T
    metrics_per_grid.columns=["version", "region", "IoU", "overseg", "underseg", "location_sim"]
    metrics_per_grid.fillna(0, inplace=True)
    
    return match_metrics_per_grid

def instance_field_accuracy(RefShp, PredVector, out_name, crop_classes=[1]):

    RefPolys = gpd.read_file(RefShp)
    RefChips=RefShp.replace("_Polys", "_Chips")
    chip_df = gpd.read_file(RefChips)
    pred_grid=int(os.path.basename(PredVector).split("_")[2])

    if "PyCropSeg" in RefShp:
        RefPolys['region'] = RefPolys['region_lef']
        RefPolys['region'] = [int(i) for i in RefPolys['region']]
        RefPolys['Name'] = RefPolys['Name_left']
        RefPolys['UNQ'] = [int(str(i)[:4]) for i in RefPolys['region']]
        class_col = "class"
    else:
        RefPolys['region'] = [int(i) for i in RefPolys['region']]
        chip_df['region'] = [int(i) for i in chip_df['region']]
        class_col = "code"  
        
    RefPoly = RefPolys[RefPolys['UNQ'] == int(pred_grid)] 
    regions = [str(i) for i in list(set(RefPoly['region'].to_list()))]
    
    stats_per_grid=[]
    exclude_in_mean=[]
    for Region in sorted(regions):
        chip_shape = chip_df[chip_df["region"]==int(Region)]
        
        pred_df=gpd.read_file(PredVector)
        pred_df = pred_df.sjoin(chip_shape, how="inner")
        pred_df = gpd.clip(pred_df, chip_shape)
        pred_df['area'] = pred_df.area     
        
        ref_df = RefPoly[RefPoly["region"]==int(Region)] 
        ref_df = ref_df[ref_df[class_col].isin(crop_classes)] 
        ref_df = gpd.clip(ref_df, chip_shape)
        
        if len(ref_df) > 0 and len(pred_df) > 0:
            ref_df['area'] = ref_df.area
            ref_df['Rindex']= ref_df.index 
            pred_df['Pindex']= pred_df.index
            if "PyCropSeg" in RefShp: 
                pred_df=pred_df.drop(columns=["index_right", "UNQ8858", "Shape_Leng", "Shape_Area", "Name", "region"])
            else:
                pred_df=pred_df.drop(columns=[i for i in pred_df.columns.to_list() if "_left" in i or  "_right" in i])
            ref_df=ref_df.drop(columns=[i for i in ref_df.columns.to_list() if "_left" in i or  "_right" in i])
            ## FIND PRED MATCH FOR EACH REF VECTOR BASED ON LARGEST OVERLAP 
            RP_index_matches = largest_overlap(ref_df, pred_df)
            ## CALCULATE ACCURACY METRICS w/ MATCHES 
            chip_avg_metrics = calc_metrics(PredVector, ref_df, pred_df, RP_index_matches)
            ## append to find average of all chips in the UNQ grid cell
            stats_per_grid.append(chip_avg_metrics)
        elif len(ref_df) == 0 and len(pred_df) == 0:
            stats_per_grid.append([os.path.basename(PredVector), Region, 1, 1, 1, 1])
            exclude_in_mean.append(Region)
        else:
            print('fix')
            print(len(pred_df))
            print(len(ref_df))
            
    print('list of chip regions w/ 0 crops: '+str(exclude_in_mean))

    stats_df=pd.DataFrame(stats_per_grid)
    stats_df.columns=["version", "region", "IoU", "overseg", "underseg", "location_sim"]
    stats_df = stats_df[~stats_df['region'].isin(exclude_in_mean)]
    print(stats_df)
    
    avg_per_grid = [str(Region)[:4], os.path.basename(PredVector), np.mean(stats_df['IoU']), np.mean(stats_df['overseg']), np.mean(stats_df['underseg']), np.mean(stats_df['location_sim']) ]
    out=pd.DataFrame(avg_per_grid).T
    out.columns=["UNQ", "version", "IoU", "overseg", "underseg", "location_sim"]
    out.to_csv(out_name)
    print(out)

    return out 





