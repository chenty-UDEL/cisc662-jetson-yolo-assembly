"""Offline analysis of 5 paired runs. Standard library only; never pools datasets A/B/C."""
import argparse
import csv
import json
import math
import statistics as stats
import sys
from collections import Counter,defaultdict
from pathlib import Path
from common import sha,save,load,csvout
from compare_detections import pair,iou,metrics
from control_checks import read_samples,evaluate,percentile

if hasattr(sys.stdout,'reconfigure'):sys.stdout.reconfigure(encoding='utf-8')

BACKENDS=('pytorch_fp32','tensorrt_fp16')
CLASSES=(9,11)

def distribution(values):
    values=list(values)
    return dict(n=len(values),mean=stats.mean(values),p50=percentile(values,.5),p95=percentile(values,.95),min=min(values),max=max(values))

def counts(tp,fp,fn):
    return dict(tp=tp,fp=fp,fn=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)

def overlap_detection_area(a,b):
    inter=max(0,min(a[2],b[2])-max(a[0],b[0]))*max(0,min(a[3],b[3])-max(a[1],b[1]))
    area=max(0,a[2]-a[0])*max(0,a[3]-a[1])
    return inter/area if area else 0

def gt_score(predictions,annotations):
    """Confidence-ordered same-class, IoU >= .5. Crowd uses COCO bbox IoA ignore."""
    truth=[];crowd=[]
    for a in annotations:
        x,y,w,h=a['bbox'];c={10:9,13:11}[a['category_id']]
        box=[x,y,x+w,y+h,1.,c]
        (crowd if a.get('iscrowd',0) else truth).append(box)
    used=set();tp=fp=ignored=0
    for p in sorted(predictions,key=lambda p:-p[4]):
        possible=[(iou(p,g),j) for j,g in enumerate(truth) if j not in used and int(p[5])==int(g[5])]
        best=max(possible,default=(0.,-1))
        if best[0]>=.5:
            used.add(best[1]);tp+=1
        elif any(int(p[5])==int(g[5]) and overlap_detection_area(p,g)>=.5 for g in crowd):ignored+=1
        else:fp+=1
    return dict(**counts(tp,fp,len(truth)-len(used)),ignored_crowd_predictions=ignored,ground_truth_instances=len(truth))

def analyze(root):
    root=root.resolve();out=root/'analysis';out.mkdir(exist_ok=True)
    cfg=load(root/'config.json');manifest=load(root/'input_manifest.json');dataset=load(root/'dataset/dataset_manifest.json');gt=load(root/'dataset/annotations/instances_coco400.json')
    frames=manifest['frames'];ids=[f['frame_id'] for f in frames];byid={r['frame_id']:r for r in dataset['frames']}
    assert len(frames)==400 and len(set(ids))==400 and set(ids)==set(byid)
    assert Counter(r['group'] for r in byid.values())=={'positive':200,'negative':200}
    assert cfg['frames']==400 and cfg['rounds']==5 and cfg['warmup']==50
    assert cfg['classes']==[9,11] and cfg['shape']==[1,3,640,640] and cfg['confidence']==.2 and cfg['nms_iou']==.7 and cfg['max_det']==300
    assert sha(root/'input_manifest.json')==cfg['manifest_sha256']
    for f in frames:
        assert sha(root/f['path'])==f['file_sha256'],f['path']
        assert sha(root/f['source'])==f['source_sha256'],f['source']
    ground=defaultdict(list)
    for a in gt['annotations']:ground[a['image_id']].append(a)
    for fid,r in byid.items():assert bool(ground[r['coco_image_id']])==(r['group']=='positive')
    allrows=[];dets={};warmups=0;workers=[];summary_rows=[];timing={};per_run_gt={};background=[];gt_rows=[]
    samples=read_samples(root/'controls/frequency_load_samples.jsonl');plan=load(root/'controls/control_plan.json');control_results={}
    expected_paths=set()
    for ri in range(1,6):
        rid=f'round_{ri:02d}'
        for backend in BACKENDS:
            folder=root/'runs'/rid/backend;expected_paths.add(folder/'measurements.csv')
            with (folder/'measurements.csv').open(encoding='utf-8',newline='') as f:rows=list(csv.DictReader(f))
            predictions=[json.loads(line) for line in (folder/'detections.jsonl').read_text('utf-8').splitlines()]
            assert len(rows)==len(predictions)==400 and [r['frame_id'] for r in rows]==ids
            assert [d['frame_id'] for d in predictions]==ids
            worker=load(folder/'worker.json');workers.append(worker)
            assert worker['measured_count']==400 and worker['warmup_count']==50 and worker['exit_code']==0
            assert worker['backend']==backend and worker['run_id']==rid and worker['valid']
            assert worker['config_sha256']==sha(root/'config.json') and worker['source_sha256']==sha(root/'src/benchmark.py') and worker['environment_sha256']==sha(root/'environment.json')
            assert worker['precision']['tf32_matmul'] is False and worker['precision']['tf32_cudnn'] is False and worker['precision']['amp'] is False
            warm=load(folder/'warmup.json');assert len(warm)==50;warmups+=len(warm)
            for r in rows:
                assert r['backend']==backend and r['run_id']==rid and r['experiment_id']==cfg['experiment_id']
                assert int(r['backend_order'])==cfg['order'][ri-1].index(backend)+1
                for key in ('preprocess_ms','inference_ms','postprocess_ms','total_ms'):
                    r[key]=float(r[key]);assert math.isfinite(r[key]) and r[key]>=0
                assert abs(r['total_ms']-sum(r[k] for k in ('preprocess_ms','inference_ms','postprocess_ms')))<1e-6
                assert int(r['end_unix_ns'])>=int(r['start_unix_ns'])
                r['group']=byid[r['frame_id']]['group'];allrows.append(r)
            for d in predictions:
                assert d['backend']==backend and d['run_id']==rid and d['classes']==[9,11]
                for b in d['boxes']:
                    assert len(b)==6 and all(math.isfinite(v) for v in b) and int(b[5]) in CLASSES and 0<=b[4]<=1
                    assert b[2]>=b[0] and b[3]>=b[1]
                dets[(rid,backend,d['frame_id'])]=d
            for group in ('all','positive','negative'):
                selected=[r for r in rows if group=='all' or r['group']==group]
                timing[f'{rid}/{backend}/{group}']={k:distribution(r[k] for r in selected) for k in ('preprocess_ms','inference_ms','postprocess_ms','total_ms')}
            formal=[x for x in samples if worker['measurement_start_ns']<=x['timestamp_ns']<=worker['measurement_end_ns']]
            check=evaluate(formal,plan);recorded=load(root/'controls'/f'{rid}_{backend}.json')
            check['static_before_passed']=recorded['static_before']['passed'];check['static_after_passed']=recorded['static_after']['passed']
            check['passed']=check['passed'] and check['static_before_passed'] and check['static_after_passed'];control_results[f'{rid}/{backend}']=check
            for category in ('all',9,11):
                scores=[];false_images=boxes_in_negative=0;positive_detected=0
                for fid in ids:
                    r=byid[fid];pred=dets[(rid,backend,fid)]['boxes'];aa=ground[r['coco_image_id']]
                    if category!='all':
                        pred=[b for b in pred if int(b[5])==category];aa=[a for a in aa if {10:9,13:11}[a['category_id']]==category]
                    score=gt_score(pred,aa);scores.append(score)
                    gt_rows.append(dict(run_id=rid,backend=backend,class_id=category,frame_id=fid,group=r['group'],**score))
                    if r['group']=='negative':
                        false_images+=bool(pred);boxes_in_negative+=len(pred)
                    else:positive_detected+=bool(pred)
                pooled=counts(*(sum(s[k] for s in scores) for k in ('tp','fp','fn')))
                pooled.update(ignored_crowd_predictions=sum(s['ignored_crowd_predictions'] for s in scores),ground_truth_instances=sum(s['ground_truth_instances'] for s in scores))
                per_run_gt[f'{rid}/{backend}/{category}']=pooled
                background.append(dict(run_id=rid,backend=backend,class_id=category,negative_images=200,negative_images_with_prediction=false_images,image_false_positive_rate=false_images/200,negative_prediction_boxes=boxes_in_negative,positive_images_with_prediction=positive_detected))
    assert set(root.glob('runs/*/*/measurements.csv'))==expected_paths,'Unexpected extra run files'
    assert len(allrows)==4000 and len(dets)==4000 and warmups==500
    for backend in BACKENDS:
        for group in ('all','positive','negative'):
            subset=[r for r in allrows if r['backend']==backend and (group=='all' or r['group']==group)]
            timing[f'pooled/{backend}/{group}']={k:distribution(r[k] for r in subset) for k in ('preprocess_ms','inference_ms','postprocess_ms','total_ms')}
    for key,value in timing.items():
        for stage,s in value.items():summary_rows.append(dict(group=key,stage=stage,**s))
    agreement_groups=defaultdict(lambda:dict(tp=0,fp=0,fn=0,ious=[],diffs=[]));match_rows=[]
    for ri in range(1,6):
        rid=f'round_{ri:02d}'
        for fid in ids:
            aa=dets[(rid,BACKENDS[0],fid)]['boxes'];bb=dets[(rid,BACKENDS[1],fid)]['boxes']
            matched,ua,ub=pair(aa,bb,.5)
            for category in ('all',9,11):
                m=[v for v in matched if category=='all' or int(aa[v[0]][5])==category]
                fn=sum(category=='all' or int(aa[i][5])==category for i in ua);fp=sum(category=='all' or int(bb[j][5])==category for j in ub)
                for key in (f'{rid}/{category}',f'pooled/{category}'):
                    g=agreement_groups[key];g['tp']+=len(m);g['fp']+=fp;g['fn']+=fn;g['ious'] += [v[2] for v in m];g['diffs'] += [v[3] for v in m]
            for i,j,overlap,diff in matched:match_rows.append(dict(run_id=rid,frame_id=fid,class_id=int(aa[i][5]),status='matched',pt_index=i,trt_index=j,iou=overlap,abs_confidence_difference=diff))
            for i in ua:match_rows.append(dict(run_id=rid,frame_id=fid,class_id=int(aa[i][5]),status='unmatched_pt',pt_index=i,trt_index='',iou='',abs_confidence_difference=''))
            for j in ub:match_rows.append(dict(run_id=rid,frame_id=fid,class_id=int(bb[j][5]),status='unmatched_trt',pt_index='',trt_index=j,iou='',abs_confidence_difference=''))
    agreement={key:metrics(g['tp'],g['fp'],g['fn'],g['ious'],g['diffs']) for key,g in agreement_groups.items()}
    def agree_pass(m):
        return m['F1'] is not None and m['F1']>=.95 and m['mean_matched_iou'] is not None and m['mean_matched_iou']>=.90 and m['mean_abs_confidence_difference'] is not None and m['mean_abs_confidence_difference']<=.05
    agreement_pass=all(agree_pass(agreement[f'pooled/{c}']) for c in ('all',9,11))
    pt=timing['pooled/pytorch_fp32/all'];trt=timing['pooled/tensorrt_fp16/all']
    reduction=100*(1-trt['inference_ms']['p50']/pt['inference_ms']['p50']);speedup=pt['inference_ms']['p50']/trt['inference_ms']['p50']
    paired=[dict(round=i,inference_speedup=timing[f'round_{i:02d}/pytorch_fp32/all']['inference_ms']['p50']/timing[f'round_{i:02d}/tensorrt_fp16/all']['inference_ms']['p50']) for i in range(1,6)]
    prior=load(root/'old_experiment_before.json');old=Path(prior['root'])
    if old.is_dir():
        after={str(p.relative_to(old)).replace('\\','/'):sha(p) for p in sorted(old.rglob('*')) if p.is_file() and not p.is_symlink()}
        save(root/'old_experiment_after.json',dict(root=str(old),sha256=after))
    elif (root/'old_experiment_after.json').exists():after=load(root/'old_experiment_after.json')['sha256']
    else:after=None
    preserved=after==prior['sha256'] if after is not None else None
    save(root/'old_preservation_check.json',dict(passed=preserved,before_files=len(prior['sha256']),after_files=len(after) if after is not None else None))
    declared=load(root/'controls/control_validation.json');restore=load(root/'controls/restoration_log.json')
    idle=load(root/'controls/pre_worker_checks.json');idle_ok=len(idle)==10 and all(x['idle']['passed'] and x['static']['passed'] for x in idle)
    # A pre-worker check can repeat while waiting; validate the check selected by each worker.
    run_manifest=load(root/'run_manifest.json')
    idle_ok=len(run_manifest)==10 and all(idle[r['pre_worker_check_index']]['idle']['passed'] and idle[r['pre_worker_check_index']]['static']['passed'] for r in run_manifest)
    controls_pass=declared['passed'] and all(c['passed'] for c in control_results.values()) and idle_ok
    result=dict(experiment_id=cfg['experiment_id'],complete=True,formal_rows=4000,formal_warmup_rows=500,unique_images=400,dataset_statistics=dataset['statistics'],timing=timing,paired_rounds=paired,model_inference_p50_reduction_pct=reduction,model_inference_speedup=speedup,total_p50_reduction_pct=100*(1-trt['total_ms']['p50']/pt['total_ms']['p50']),processing_fps={b:1000/timing[f'pooled/{b}/all']['total_ms']['mean'] for b in BACKENDS},proposal_speed_target_passed=reduction>=30,agreement=agreement,agreement_targets_passed=agreement_pass,ground_truth_metrics_per_run=per_run_gt,negative_false_positives_per_run=background,controls_recomputed=control_results,controls_passed=controls_pass,restoration_passed=restore['passed'],old_data_preserved=preserved,acceptance_passed=controls_pass and restore['passed'] and preserved is True and agreement_pass and reduction>=30,metric_notes=['GT precision/recall/F1 are at confidence 0.20 and bbox IoU 0.50, not COCO mAP. Crowd matches use bbox IoA ignore.','GT metrics are reported separately for each of five repetitions of the same 400 images; repetitions are not additional independent images.','Agreement uses the same deterministic same-class IoU-descending greedy matching as the earlier A experiment.','This is a curated 50/50 target-presence subset, not the full COCO validation benchmark or representative traffic deployment prevalence. Negatives include general background scenes.','COCO labels and AI visual screening are imperfect; no independent human exhaustive relabeling was performed.','A, B and this new dataset must remain separate. JPEG/PNG decode, drawing and disk I/O are excluded from timed stages.'])
    save(out/'results.json',result);csvout(out/'timing_summary.csv',summary_rows);csvout(out/'paired_rounds.csv',paired);csvout(out/'ground_truth_per_image.csv',gt_rows);csvout(out/'negative_false_positives.csv',background)
    csvout(out/'backend_matches.csv',match_rows,['run_id','frame_id','class_id','status','pt_index','trt_index','iou','abs_confidence_difference'])
    csvout(root/'measurements.csv',allrows)
    with (root/'detections.jsonl').open('w',encoding='utf-8') as f:
        for key in sorted(dets):f.write(json.dumps(dets[key])+'\n')
    summary=f'''COCO400 实验结果\n\n独立图片 400 张：阳性 200、阴性 200。两种后端各 5 轮，正式计时 4000 条；正式轮预热 500 次，另有独立 smoke 记录。\n\n模型推理中位数：PyTorch FP32 {pt['inference_ms']['p50']:.4f} ms；TensorRT FP16 {trt['inference_ms']['p50']:.4f} ms。下降 {reduction:.2f}%，加速 {speedup:.3f} 倍。30% 目标是否达到：{reduction>=30}。\n\n控制条件通过：{controls_pass}；机器状态恢复：{restore['passed']}；旧数据保留：{preserved}；两后端一致性通过：{agreement_pass}。总体验收：{result['acceptance_passed']}。\n\n真实标注准确性见 results.json 的 ground_truth_metrics_per_run；每轮分别统计，不能把五轮当作 2000 张新图片。背景误报见 negative_false_positives.csv。后端一致性不等于识别准确率。该子集的固定阈值 precision/recall 不应写成完整 COCO mAP。\n'''
    (out/'SUMMARY_ZH.txt').write_text(summary,encoding='utf-8')
    print(summary);return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);a=p.parse_args()
    try:
        result=analyze(a.bundle)
        if not result['controls_passed'] or not result['restoration_passed'] or result['old_data_preserved'] is not True:raise SystemExit(2)
    except Exception as e:
        a.bundle.joinpath('analysis').mkdir(exist_ok=True)
        save(a.bundle/'analysis/incomplete_or_invalid.json',dict(complete=False,error=repr(e)))
        raise
