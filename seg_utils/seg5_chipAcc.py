#!/usr/bin/ python
import os, sys
import cnet_funcs as cf
import instance_accuracy as ia

def main():
    version_dir = sys.argv[1]
    method = sys.argv[2]
    thresh = sys.argv[3]
    RefShp = sys.argv[4]
    predPoly_dir=os.path.join(version_dir, "infer_polys_"+method+"_"+thresh.replace(".", "pt"))
    pred_prefix=method+"_pred_polys_"+thresh.replace(".", "pt")+"th"


    ia.chip_acc(predPoly_dir=predPoly_dir, 
             pred_prefix=pred_prefix,
             RefShp=RefShp, 
             class_col="class", 
             crop_classes=[1])

if __name__ == "__main__":
    main()




