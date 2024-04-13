#!/usr/bin/ python

import os, sys
import cnet_funcs as cf


def main():
    VI_list = sys.argv[2]
    vis = VI_list[1:-1].replace(" ", "").split(",")
    ## take training regions that have folders in time_series_vars (are ready) and make a list to populate config_cultionet.yml
    cf.ready_regions(version_dir=sys.argv[1], vi_list=vis)

if __name__ == "__main__":
    main()


