#!/usr/bin/ python

import os, sys
import json
import numpy as np
import pandas as pd
import os, sys
from pathlib import Path
import shutil
from datetime import datetime


import cnet_funcs as cf


grd = sys.argv[1]
VERS_DIR = sys.argv[2]
YEAR = int(sys.argv[3])
MMDD=sys.argv[4]
VI_list = sys.argv[5][1:-1].replaceAll(" ", "").split(",") 
PROJ_DIR=sys.argv[6]

if "AI4Boundaires" not in PROJ_DIR:
    PRED_YR = YEAR
else:
    PRED_YR = 2020

def main():
    for VI in VI_list:
        cf.copy_pred_grid(grid=grd, 
                spec_index=VI, 
                proj_stac_dir=PROJ_DIR, 
                version_dir=VERS_DIR, 
                mmdd=MM_DD, 
                end_yr=PRED_YR)

if __name__ == "__main__":
    main()

