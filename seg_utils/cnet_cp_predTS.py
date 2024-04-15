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


def main():
    for VI in sys.argv[5].split(","):
        cf.copy_pred_grid(grid=sys.argv[1], 
                spec_index=VI, 
                proj_grid_dir=sys.argv[6], 
                version_dir=sys.argv[2], 
                mmdd=sys.argv[4], 
                end_yr=int(sys.argv[3]))

if __name__ == "__main__":
    main()

