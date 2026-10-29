"""Compile the same C source to two real Linux CPU assembly targets."""
import argparse,hashlib,json,os,platform,shutil,struct,subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parent

def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--zig',default=str(ROOT/'.tools/zig-x86_64-windows-0.15.2/zig.exe'))
    args=parser.parse_args();zig=Path(args.zig).resolve()
    if not zig.is_file():raise SystemExit('Pass --zig with the path to a Zig 0.15.2 executable.')
    env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(ROOT/'.tools/global-cache');env['ZIG_LOCAL_CACHE_DIR']=str(ROOT/'.tools/local-cache')
    for d in ('assembly','objects','verification','original_project/src'):(ROOT/d).mkdir(parents=True,exist_ok=True)
    records=[]
    def run(argv):
        p=subprocess.run([str(zig),*argv],cwd=ROOT,env=env,text=True,encoding='utf-8',errors='replace',capture_output=True)
        records.append({'command':['zig',*argv],'exit_code':p.returncode,'stdout':p.stdout,'stderr':p.stderr})
        if p.returncode:raise RuntimeError(p.stderr or p.stdout)
        return p.stdout
    zig_version=run(['version']).strip()
    version=run(['cc','--version'])
    shared=['-std=c11','-O2','-Wall','-Wextra','-Werror','-Wno-unused-command-line-argument','-fno-vectorize','-fno-slp-vectorize','-fno-unroll-loops','-ffp-contract=off','-fno-ident','-gline-tables-only','-ffile-prefix-map='+str(ROOT)+'=.']
    targets=[('x86_64','x86_64-linux-gnu',['-mcpu=baseline','-masm=intel']),('armv8_aarch64','aarch64-linux-gnu',['-mcpu=baseline'])]
    for name,triple,extra in targets:
        stem='preprocess_'+name
        common=['cc','-target',triple,*shared,*extra,'src/preprocess_core.c']
        run([*common,'-S','-fverbose-asm','-o',f'assembly/{stem}.s'])
        run(['cc','-target',triple,*extra,'-c',f'assembly/{stem}.s','-o',f'objects/{stem}.o'])
        run(['cc','-target',triple,'-nostdlib','-static','-fno-pie','-no-pie','-Wl,--entry=yolo_bgr8_to_rgb_chw_f32','-Wl,--build-id=none',f'objects/{stem}.o','-o',f'verification/{stem}.elf'])
    run(['cc','-target','x86_64-windows-gnu',*shared,'src/preprocess_core.c','-shared','-o','verification/preprocess_test.dll'])
    bundle=ROOT.parent/'received_coco400_34eb40ed85/experiment_bundle'
    original=bundle if bundle.is_dir() else ROOT/'original_project'
    provenance=[]
    identity=json.loads((original/'execution_identity.json').read_text('utf-8'))
    for src in sorted((original/'src').glob('*.py')):
        name=src.name;dst=ROOT/'original_project/src'/name
        expected=identity.get('src/'+name)
        if expected:assert sha(src)==expected
        if src.resolve()!=dst.resolve():shutil.copyfile(src,dst)
        assert sha(src)==sha(dst)
        provenance.append({'original_bundle_path':'src/'+name,'copied_path':dst.relative_to(ROOT).as_posix(),'sha256':sha(dst),'matches_experiment_execution_identity':True if expected else None})
    for name in ('execution_identity.json','config.json','engine_compatibility.json'):
        src=original/name;dst=ROOT/'original_project'/name
        if src.resolve()!=dst.resolve():shutil.copyfile(src,dst)
    provenance.append({'reference_source':'src/preprocess_core.c','sha256':sha(ROOT/'src/preprocess_core.c'),'status':'New CPU reference, not part of the original measured benchmark'})
    (ROOT/'source_provenance.json').write_text(json.dumps(provenance,indent=2)+'\n',encoding='utf-8')
    result={'zig_version':zig_version,'compiler_version':version,'build_host':platform.platform(),'compiler_executable_sha256':sha(zig),'source_sha256':sha(ROOT/'src/preprocess_core.c'),'shared_flags':shared,'targets':[{'label':n,'target':t,'target_flags':e} for n,t,e in targets],'commands':records}
    (ROOT/'build_record.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'status':'compiled','targets':[t for _,t,_ in targets],'compiler':version.splitlines()[0],'commands':len(records)}))

if __name__=='__main__':main()
