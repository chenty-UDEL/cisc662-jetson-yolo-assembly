"""Small known-outcome tests for metrics that affect experimental conclusions."""
from analyze_coco400 import gt_score,counts,iou,pair,percentile

def main():
    annotation=dict(category_id=10,bbox=[0,0,10,10],iscrowd=0)
    detection=[0,0,10,10,.9,9]
    assert iou(detection,detection)==1 and iou(detection,[20,20,30,30])==0
    assert percentile([1,2,3,4],.5)==2.5
    assert gt_score([detection],[annotation])['f1']==1
    duplicate=gt_score([detection,detection],[annotation]);assert (duplicate['tp'],duplicate['fp'],duplicate['fn'])==(1,1,0)
    wrong_class=gt_score([[0,0,10,10,.9,11]],[annotation]);assert (wrong_class['tp'],wrong_class['fp'],wrong_class['fn'])==(0,1,1)
    assert gt_score([detection],[])['fp']==1
    assert gt_score([],[annotation])['fn']==1
    assert counts(0,0,0)['precision'] is None
    crowd=gt_score([detection],[dict(annotation,iscrowd=1)]);assert crowd['fp']==0 and crowd['ignored_crowd_predictions']==1
    matched,left,right=pair([detection,detection],[detection],.5);assert len(matched)==1 and len(left)==1 and not right
    assert pair([],[])[0]==[]
    print('Analysis self-tests passed (known TP/FP/FN, class mismatch, duplicate, empty and crowd cases).')

if __name__=='__main__':main()
