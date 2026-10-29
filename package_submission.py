"""Validate records and create a compact source/assembly submission archive."""
import hashlib,json,re,zipfile
from pathlib import Path

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT.parent/'Jetson_YOLO_Source_Assembly_Submission.zip'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def read(path):return json.loads((ROOT/path).read_text('utf-8'))

def main():
    source_hash=sha(ROOT/'src/preprocess_core.c')
    build=read('build_record.json');native=read('verification/reference_tests.json');emulated=read('verification/assembly_tests.json')
    assert build['source_sha256']==native['source_sha256']==source_hash
    assert native['passed'] and emulated['passed']
    for target in emulated['targets']:
        name=target['target']
        for kind,folder,extension in (('assembly','assembly','s'),('object','objects','o'),('elf','verification','elf')):
            assert target[kind+'_sha256']==sha(ROOT/f'{folder}/preprocess_{name}.{extension}')
    identity=read('original_project/execution_identity.json')
    for path in ('src/benchmark.py','src/common.py'):
        assert sha(ROOT/'original_project'/path)==identity[path]
    top=('README.md','COMPARE_EN.md','COMPARE_ZH.md','build.py','test_reference.py','verify_assembly.py','package_submission.py','requirements-verification.txt','build_record.json','source_provenance.json','compiler_download.json','.gitignore')
    files=[ROOT/p for p in top]
    files.extend(ROOT/p for p in ('SUBMISSION.md','.gitattributes') if (ROOT/p).is_file())
    for folder in ('src','assembly','objects','disassembly','original_project'):
        files.extend(p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts)
    files.extend(p for p in (ROOT/'verification').iterdir() if p.suffix in ('.json','.elf','.dll'))
    files=sorted(set(files),key=lambda p:p.relative_to(ROOT).as_posix())
    for document in (ROOT/'README.md',ROOT/'COMPARE_EN.md',ROOT/'COMPARE_ZH.md'):
        for target in re.findall(r'\]\(([^)]+)\)',document.read_text('utf-8')):
            if not target.startswith(('https://','http://')):assert (document.parent/target).exists(),target
    sums=''.join(f'{sha(path)}  {path.relative_to(ROOT).as_posix()}\n' for path in files)
    (ROOT/'SHA256SUMS').write_text(sums,encoding='utf-8')
    files.append(ROOT/'SHA256SUMS')
    with zipfile.ZipFile(OUTPUT,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as archive:
        for path in files:archive.write(path,'Jetson_YOLO_Source_Assembly/'+path.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(OUTPUT) as archive:
        assert archive.testzip() is None
        assert len(archive.infolist())==len(files)
        for path in files:
            member='Jetson_YOLO_Source_Assembly/'+path.relative_to(ROOT).as_posix()
            assert archive.read(member)==path.read_bytes()
        assert all('/.tools/' not in n and '/.runtime/' not in n for n in archive.namelist())
    print(json.dumps({'archive':str(OUTPUT),'files':len(files),'bytes':OUTPUT.stat().st_size,'sha256':sha(OUTPUT),'validation':'All archive members match local files; source, compiled artifacts and verification hashes agree'},indent=2))

if __name__=='__main__':main()
