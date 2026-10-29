"""Independent offline replay on a temporary copy; Python standard library only.

Windows: py -3 src/offline_recompute.py --bundle . --output offline_check.json
Linux:   python3 src/offline_recompute.py --bundle . --output offline_check.json
"""
import argparse
import hashlib
import json
import math
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def compare(a, b, path='root'):
    if isinstance(a, bool) or isinstance(b, bool):
        assert type(a) is type(b) and a == b, path
    elif isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if isinstance(a, int) and isinstance(b, int):
            assert a == b, path
        else:
            assert math.isclose(a, b, rel_tol=1e-10, abs_tol=1e-9), (path, a, b)
    elif isinstance(a, dict) and isinstance(b, dict):
        assert a.keys() == b.keys(), path
        for k in a:
            compare(a[k], b[k], path + '/' + k)
    elif isinstance(a, list) and isinstance(b, list):
        assert len(a) == len(b), path
        for i, (x, y) in enumerate(zip(a, b)):
            compare(x, y, path + '/' + str(i))
    else:
        assert type(a) is type(b) and a == b, (path, a, b)


def main():
    p=argparse.ArgumentParser();p.add_argument('--bundle',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    root=a.bundle.resolve();verified=0
    if (root/'SHA256SUMS').exists():
        for line in (root/'SHA256SUMS').read_text(encoding='utf-8').splitlines():
            expected,rel=line.split('  ',1);f=(root/rel).resolve()
            assert f.is_relative_to(root) and f.is_file(),rel
            assert hashlib.sha256(f.read_bytes()).hexdigest()==expected,rel
            verified+=1
    expected={name:json.loads((root/'analysis'/name).read_text(encoding='utf-8')) for name in ['results.json','supplementary_validation.json','A_C_comparison.json']}
    expected_svg={f.name:f.read_bytes() for f in (root/'analysis').glob('*.svg')}
    with tempfile.TemporaryDirectory(prefix='coco400_offline_') as tmp:
        copied=Path(tmp)/'experiment_bundle'
        shutil.copytree(root,copied,ignore=shutil.ignore_patterns('__pycache__','analysis'))
        logs={}
        for script in ['selftest_analysis.py','analyze_coco400.py','supplement_report.py']:
            args=[sys.executable,str(copied/'src'/script)]
            if script!='selftest_analysis.py':args+=['--bundle',str(copied)]
            r=subprocess.run(args,capture_output=True,text=True,encoding='utf-8',errors='replace')
            logs[script]=dict(returncode=r.returncode,stdout=r.stdout,stderr=r.stderr)
            assert r.returncode==0,logs[script]
        for name,baseline in expected.items():compare(baseline,json.loads((copied/'analysis'/name).read_text(encoding='utf-8')),name)
        for name,baseline in expected_svg.items():assert baseline==(copied/'analysis'/name).read_bytes(),name
    result=dict(passed=True,platform=platform.platform(),python=platform.python_version(),sha256_files_verified=verified,recomputed_json=list(expected),identical_svg=list(expected_svg),numeric_tolerance=dict(relative=1e-10,absolute=1e-9),logs=logs,note='Actual platform stated above; no CUDA, network, TensorRT or third-party Python packages used. Native Windows execution is not implied by a Linux result.')
    a.output.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    print('Independent offline replay passed:',a.output)


if __name__=='__main__':main()
