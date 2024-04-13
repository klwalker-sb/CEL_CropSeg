#!/usr/bin/ python

import os, sys

import cnet_funcs as cf
    
def main():
    ### look in user_train directory, for user input grid cell, grab all regions within that grid cell and clip chip for each region (rgn1-evi2, rgn2-evi2, rgn1-gcvi, rgn2-gcvi, rgn1-wi, rgn2-wi) 

    cf.clip_chip(
    grid_num=sys.argv[1], 
    spec_ind=sys.argv[2], 
    proj_stac_dir=sys.argv[3], 
    version_dir=sys.argv[4], 
    grid_file=sys.argv[5], 
    end_yr=int(sys.argv[6])
    )


if __name__ == "__main__":
    main()