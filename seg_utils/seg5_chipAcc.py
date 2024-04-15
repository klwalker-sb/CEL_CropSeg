#!/usr/bin/ python
import os, sys
import cnet_funcs as cf
import instance_accuracy as ia

def main():
    version_dir = sys.argv[1]
    method = sys.argv[2]
    thresh = sys.argv[3]

    ia.chip_acc(predPoly_dir=os.path.join(version_dir, "infer_polys_"+method+"_"+thresh.replace(".", "pt")), 
             pred_prefix=method+"_pred_polys_"+thresh.replace(".", "pt")+"th",
             RefShp=sys.argv[4], 
             class_col="class", 
             crop_classes=[1], 
             acc_id_file=sys.argv[5], 
             out_acc_dir=sys.argv[6])

if __name__ == "__main__":
    main()




