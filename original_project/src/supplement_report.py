"""Portable COCO400 reports/plots. Standard library only; no device access."""
import argparse
import csv
import html
import json
import statistics
from pathlib import Path
from common import load, save, sha, csvout
from control_checks import read_samples, evaluate


def plot(path, title, series, ylabel):
    """Small standalone SVG line chart; all original samples remain in CSV/JSONL."""
    colors = ['#1764ad', '#e27820', '#238943', '#9e4298']
    width, height = 1000, 400
    values = [y for _, points in series for _, y in points if y is not None]
    if not values:
        return
    xmax = max(x for _, points in series for x, _ in points) or 1
    ymax = max(values) * 1.12 or 1
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">', '<rect width="100%" height="100%" fill="white"/>', f'<text x="70" y="25" font-family="sans-serif" font-size="18">{html.escape(title)}</text>']
    for i in range(6):
        y = 310 - i * 48
        parts.append(f'<path d="M70 {y} H970" stroke="#ddd"/><text x="5" y="{y+4}" font-size="12">{ymax*i/5:.2f}</text>')
    parts.append('<path d="M70 70 V310 H970" fill="none" stroke="black"/>')
    for i, (label, points) in enumerate(series):
        color = colors[i % len(colors)]
        coords = ' '.join(f'{70+x/xmax*900:.2f},{310-y/ymax*240:.2f}' for x, y in points if y is not None)
        parts.append(f'<polyline points="{coords}" fill="none" stroke="{color}" stroke-width="1.5"/>')
        parts.append(f'<text x="{70+i*220}" y="355" fill="{color}" font-family="sans-serif" font-size="13">{html.escape(label)}</text>')
    parts.append(f'<text x="70" y="55" font-size="12">{html.escape(ylabel)}</text><text x="760" y="390" font-size="12">x: elapsed seconds / round index</text></svg>')
    path.write_text('\n'.join(parts), encoding='utf-8')


def report(root):
    out = root / 'analysis'
    result = load(out / 'results.json')
    plan = load(root / 'controls/control_plan.json')
    samples = read_samples(root / 'controls/frequency_load_samples.jsonl')
    idle = load(root / 'controls/pre_worker_checks.json')
    runs = load(root / 'run_manifest.json')
    checks = []
    for run in runs:
        chosen = idle[run['pre_worker_check_index']]
        window = [s for s in samples if chosen['check_ns']-15_000_000_000 <= s['timestamp_ns'] <= chosen['check_ns']]
        actual = evaluate(window, plan, 'idle')
        checks.append(dict(run_id=run['run_id'], backend=run['backend'], recomputed_idle=actual,
                           cooldown_seconds=(chosen['check_ns']-chosen['cooldown_start_ns'])/1e9,
                           passed=actual['passed'] and chosen['actual_wait_seconds']>=30 and chosen['static']['passed']))
    smoke = []
    for backend in ('pytorch_fp32', 'tensorrt_fp16'):
        folder = root/'smoke/preflight'/backend
        worker = load(folder/'worker.json')
        with (folder/'measurements.csv').open(encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        smoke.append(dict(backend=backend, measured=len(rows), warmups=len(load(folder/'warmup.json')),
                          passed=len(rows)==8 and worker['measured_count']==8 and len(load(folder/'warmup.json'))==50))
    consistency = []
    for key, metrics in result['agreement'].items():
        consistency.append(dict(group=key, **metrics, targets_passed=metrics['status']=='evaluable' and metrics['F1']>=.95 and metrics['mean_matched_iou'] is not None and metrics['mean_matched_iou']>=.9 and metrics['mean_abs_confidence_difference']<=.05))
    csvout(out/'agreement_summary.csv', consistency)
    ground_summary=[]
    for key,metrics in result['ground_truth_metrics_per_run'].items():
        run_id,backend,category=key.split('/')
        ground_summary.append(dict(run_id=run_id,backend=backend,class_id=category,**metrics))
    csvout(out/'ground_truth_summary.csv',ground_summary)
    rows = []
    for key, stages in result['timing'].items():
        rows.append(dict(group=key, images=stages['total_ms']['n'], processing_fps=1000/stages['total_ms']['mean']))
    csvout(out/'processing_fps_by_group.csv', rows)
    paired = []
    for i in range(1,6):
        pt=result['timing'][f'round_{i:02d}/pytorch_fp32/all']['inference_ms']['p50']
        trt=result['timing'][f'round_{i:02d}/tensorrt_fp16/all']['inference_ms']['p50']
        paired.append(dict(round=i,pt_inference_p50_ms=pt,trt_inference_p50_ms=trt,speedup=pt/trt,reduction_pct=100*(1-trt/pt),target_passed=trt/pt<=.7))
    csvout(out/'paired_rounds_expanded.csv',paired)
    # Detailed unmatched coordinates/confidences, in addition to the primary index list.
    dets={}
    for line in (root/'detections.jsonl').read_text(encoding='utf-8').splitlines():
        d=json.loads(line);dets[(d['run_id'],d['frame_id'],d['backend'])]=d['boxes']
    unmatched=[]
    with (out/'backend_matches.csv').open(encoding='utf-8') as f:
        for row in csv.DictReader(f):
            if row['status']=='matched':continue
            backend='pytorch_fp32' if row['status']=='unmatched_pt' else 'tensorrt_fp16'
            index=int(row['pt_index'] if backend=='pytorch_fp32' else row['trt_index'])
            unmatched.append(dict(**row,backend=backend,box=dets[(row['run_id'],row['frame_id'],backend)][index]))
    save(out/'unmatched_boxes.json',unmatched)
    # Portable preservation check for the additional v1 and B before/after snapshots.
    previous=load(root/'additional_old_before.json')
    after_path=root/'additional_old_after.json'
    if all(Path(p).is_dir() for p in previous):
        after={name:{str(p.relative_to(Path(name))):sha(p) for p in sorted(Path(name).rglob('*')) if p.is_file() and not p.is_symlink()} for name in previous}
        save(after_path,after)
    else:after=load(after_path)
    preservation={name:dict(passed=before==after[name],files=len(before)) for name,before in previous.items()}
    save(out/'additional_old_preservation.json',preservation)
    origin=load(root/'controls/restoration_log.json')
    evidence=dict(idle_checks=checks,smoke=smoke,additional_old_preservation=preservation,
                  idle_and_cooldown_passed=len(checks)==10 and all(c['passed'] for c in checks),
                  smoke_passed=all(c['passed'] for c in smoke),
                  agreement_each_round_and_class_passed=all(c['targets_passed'] for c in consistency),
                  monitor_overhead=load(root/'controls/monitor_overhead.json'),
                  formal_control_summaries={k:dict(gpu_active_samples=v['gpu_active_samples'],gpu_within_fraction=v['gpu']['within_fraction'],background_cpu_p95=v['background_cpu']['p95'],max_temperature_c=v['max_temperature_c'],passed=v['passed']) for k,v in result['controls_recomputed'].items()})
    evidence['all_required_evidence_passed']=result['acceptance_passed'] and evidence['idle_and_cooldown_passed'] and evidence['smoke_passed'] and evidence['agreement_each_round_and_class_passed'] and all(x['passed'] for x in preservation.values())
    save(out/'supplementary_validation.json',evidence)
    # All telemetry records, without removing outliers or missing values.
    telemetry=[]
    t0=samples[0]['timestamp_ns']
    for s in samples:
        telemetry.append(dict(timestamp_ns=s['timestamp_ns'],elapsed_s=(s['timestamp_ns']-t0)/1e9,gpu_mhz=s['gpu_hz']/1e6 if s['gpu_hz'] is not None else None,emc_mhz=s['emc_hz']/1e6 if s['emc_hz'] is not None else None,
                              gpu_util_pct=s['gpu_util_pct'],background_cpu_pct_one_core=s['background_cpu_pct_one_core'],monitor_cpu_pct_one_core=s['monitor_cpu_pct_one_core'],tegrastats_age_ms=s['tegrastats_age_ms'],
                              **{'cpu'+str(i)+'_mhz':v/1000 if v is not None else None for i,v in enumerate(s['cpu_khz'])},
                              max_core_temperature_c=max((v for k,v in s['temperatures_c'].items() if k in ('gpu','cpu','tj')),default=None)))
    csvout(out/'telemetry.csv',telemetry)
    plot(out/'inference_p50.svg','COCO400 inference p50 by round',[(b,[(r['round'],r[k]) for r in paired]) for b,k in [('PyTorch FP32','pt_inference_p50_ms'),('TensorRT FP16','trt_inference_p50_ms')]],'milliseconds')
    for field,label in [('gpu_mhz','GPU actual MHz'),('emc_mhz','EMC actual MHz'),('background_cpu_pct_one_core','Background CPU percent of one core'),('max_core_temperature_c','Core temperature Celsius')]:
        plot(out/(field+'.svg'),label,[(label,[(r['elapsed_s'],r[field]) for r in telemetry])],label)
    # A is a separate dataset, supplied as a read-only reference copy.
    a=load(root/'comparison_reference/A_summary.json')
    comparison=[]
    for backend in ('pytorch_fp32','tensorrt_fp16'):
        old=a['statistics']['pooled/'+backend];new=result['timing']['pooled/'+backend+'/all']
        comparison.append(dict(experiment='A_original_300',backend=backend,unique_images=300,formal_rows=1500,inference_p50_ms=old['inference_ms_p50'],inference_p95_ms=old['inference_ms_p95'],total_p50_ms=old['total_ms_p50'],processing_fps=old['serial_detection_fps']))
        comparison.append(dict(experiment='C_COCO400',backend=backend,unique_images=400,formal_rows=2000,inference_p50_ms=new['inference_ms']['p50'],inference_p95_ms=new['inference_ms']['p95'],total_p50_ms=new['total_ms']['p50'],processing_fps=result['processing_fps'][backend]))
    csvout(out/'A_C_comparison.csv',comparison)
    save(out/'A_C_comparison.json',dict(timing=comparison,A=dict(unique_frames=300,formal_rows=3000,inference_reduction_pct=a['inference_latency_reduction_percent'],agreement=a['agreement']['pooled/all']),C=dict(unique_frames=400,formal_rows=4000,inference_reduction_pct=result['model_inference_p50_reduction_pct'],agreement=result['agreement']['pooled/all']),note='Separate image distributions and measurement sessions. No pooling, no causal attribution of A/C difference. B has no formal measurements.'))
    lines=['# COCO400 补充实验详细结果','',f"总体验收（含重新计算的启动前窗口、预热和旧数据校验）：{evidence['all_required_evidence_passed']}。",'', '| 数据集 | 正式计时 | 推理中位延迟降低 |','|---|---:|---:|', f"| A（原 300 帧） | 3000 | {a['inference_latency_reduction_percent']:.2f}% |",f"| C（COCO400） | 4000 | {result['model_inference_p50_reduction_pct']:.2f}% |",'', 'B 原素材不足，未正式计时。A/C 使用不同图片及不同测量会话，分别统计，不据此归因速度变化。','', '| 后端 | 推理 p50 ms | 推理 p95 ms | 总耗时 p50 ms | processing FPS |','|---|---:|---:|---:|---:|']
    for b in ('pytorch_fp32','tensorrt_fp16'):
        t=result['timing'][f'pooled/{b}/all'];lines.append(f"| {b} | {t['inference_ms']['p50']:.4f} | {t['inference_ms']['p95']:.4f} | {t['total_ms']['p50']:.4f} | {result['processing_fps'][b]:.2f} |")
    lines += ['', '全体/阳性/阴性各阶段 p50、p95、均值见 timing_summary.csv，分组 processing FPS 见 processing_fps_by_group.csv，逐轮配对见 paired_rounds_expanded.csv。','', '| 一致性类别 | F1 | 平均匹配 IoU | 平均置信度绝对差 | 可评价/通过 |','|---|---:|---:|---:|---|']
    for c in ('all',9,11):
        m=result['agreement'][f'pooled/{c}'];passed=next(r['targets_passed'] for r in consistency if r['group']==f'pooled/{c}')
        lines.append(f"| {c} | {m['F1']:.6f} | {m['mean_matched_iou']:.6f} | {m['mean_abs_confidence_difference']:.6f} | {m['status']} / {passed} |")
    lines += ['', '| 后端 / 类别（第一轮，其他轮分别保留） | precision | recall | F1 | TP / FP / FN | crowd 忽略预测 |','|---|---:|---:|---:|---|---:|']
    for b in ('pytorch_fp32','tensorrt_fp16'):
        for c in ('all',9,11):
            m=result['ground_truth_metrics_per_run'][f'round_01/{b}/{c}'];lines.append(f"| {b} / {c} | {m['precision']:.4f} | {m['recall']:.4f} | {m['f1']:.4f} | {m['tp']} / {m['fp']} / {m['fn']} | {m['ignored_crowd_predictions']} |")
    lines += ['', '以上为 confidence=0.20、IoU=0.50 的固定阈值指标，不是 COCO mAP。587 条原始目标标注含 3 条 crowd；crowd 不作为普通独立目标，匹配用预测框面积 IoA≥0.5 忽略。逐轮、逐类完整表见 ground_truth_summary.csv。','']
    for r in result['negative_false_positives_per_run']:
        if r['run_id']=='round_01' and r['class_id']=='all':lines.append(f"第一轮 {r['backend']}：200 张阴性中 {r['negative_images_with_prediction']} 张误报、{r['negative_prediction_boxes']} 个框，图片误报率 {r['image_false_positive_rate']:.2%}；200 张阳性中 {r['positive_images_with_prediction']} 张有预测。")
    lines += ['', '唯一阴性误报图为 dataset/images/negative/000000550939.jpg。AI 复查可见画面下方灰色近八角形路牌背面，两后端在该区域预测停车标志。原始 COCO 目标标注为空，仍按冻结标签统计误报，未修改样本或标注；这暴露了阴性定义和视觉筛选的局限。复查记录见 samples/negative_case_review.json。', '', '验收通过指协议完整性、控制条件、速度目标及后端一致性；任务未设真值 precision/recall 的通过门槛。以上较低的交通灯 recall 仍是模型识别能力的实际限制。']
    overhead=evidence['monitor_overhead']
    lines += ['', f"监测 CPU 开销：{overhead['cpu_fraction_of_one_core']:.4f} 个 CPU 核；100ms 频率读取平均 {overhead['frequency_query_mean_wall_us']:.1f} µs。相同门槛不等于各会话后台负载完全一致；实际各 worker 频率/温度/后台分位值见 supplementary_validation.json，原始异常未删除。未另做无监测对照，无法量化监测对延迟的扰动。",'', f"状态恢复通过：{origin['passed']}；静态设置差异：{origin['static_state_differences']}。SIGCONT 成功只表示原 PID 已收到恢复信号。后续检查中八个原 PID 仍运行/休眠，一个 RustDesk 子进程退出，已观察到同用户的新子进程，RustDesk 服务仍 active；未手动重启服务。完整记录见 controls/process_restoration_verification.json。",'', '复用 A 的固定 640 引擎，PyTorch、CUDA、TensorRT、Ultralytics 版本核验通过。引擎内部启用 FP16；实际输入输出为 FP32，不能声称所有层或 I/O 都是 FP16。', '', '400 张图是 AI 视觉复核且阳性/阴性按 1:1 筛选的 COCO val2017 子集；五轮重复使用同一批图片。两后端一致不代表检测正确，不能当作实际道路普遍准确率或 2000 张独立准确性样本。', '', 'Windows：安装 Python 3.12 后，解压到独立目录，在 experiment_bundle 中运行 `py -3 src/offline_recompute.py --bundle . --output offline_check.json`。它先校验逐文件 SHA256，再在临时副本重新分析并比对 JSON/SVG；仅 Python 标准库，无需 CUDA/网络。本次实际独立复算平台记录在 offline_verification.json，未声称已在 Windows 原生验证。']
    (out/'REPORT_ZH.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    print('Supplementary reports and SVG/CSV completed:',out)
    return evidence


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);a=p.parse_args();report(a.bundle.resolve())
