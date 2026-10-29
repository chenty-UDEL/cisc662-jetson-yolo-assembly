"""Disassemble and functionally emulate the exact assembled Linux functions.

Optional dependencies: unicorn==2.1.4 and capstone==5.0.9. Emulation checks
functional results only; it does not measure hardware or Jetson performance.
"""
import hashlib,json,random,struct,sys
from pathlib import Path

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'.runtime/python'))
import capstone
import unicorn
from unicorn import x86_const as xr,arm64_const as ar

SYMBOL='yolo_bgr8_to_rgb_chw_f32'

def read_elf(path):
    data=path.read_bytes()
    header=struct.unpack_from('<16sHHIQQQIHHHHHH',data)
    assert header[0][:6]==b'\x7fELF\x02\x01','Expected little-endian ELF64'
    machine,entry,phoff,shoff=header[2],header[4],header[5],header[6]
    segments=[]
    for i in range(header[10]):
        p=struct.unpack_from('<IIQQQQQQ',data,phoff+i*header[9])
        if p[0]==1:segments.append({'address':p[3],'memory_size':p[6],'data':data[p[2]:p[2]+p[5]]})
    sections=[struct.unpack_from('<IIQQQQIIQQ',data,shoff+i*header[11]) for i in range(header[12])]
    function=None
    for section in sections:
        if section[1]!=2:continue
        strings_section=sections[section[6]]
        strings=data[strings_section[4]:strings_section[4]+strings_section[5]]
        for offset in range(section[4],section[4]+section[5],section[9]):
            name,info,other,index,value,size=struct.unpack_from('<IBBHQQ',data,offset)
            if strings[name:].split(b'\0',1)[0].decode()==SYMBOL:
                source_section=sections[index]
                start=source_section[4]+value-source_section[3]
                function={'address':value,'size':size,'data':data[start:start+size]}
    assert function and entry==function['address']
    return machine,segments,function

def mapped_size(length):return max(4096,(length+4095)&~4095)

def execute(machine,segments,function,values):
    n=len(values)//3
    src,dst,stack,sentinel=0x10000000,0x20000000,0x40000000,0x50000000
    if machine==62:
        cpu=unicorn.Uc(unicorn.UC_ARCH_X86,unicorn.UC_MODE_64)
    elif machine==183:
        cpu=unicorn.Uc(unicorn.UC_ARCH_ARM64,unicorn.UC_MODE_ARM)
    else:raise ValueError(machine)
    mapped=set()
    for segment in segments:
        first=segment['address']&~4095
        last=(segment['address']+segment['memory_size']+4095)&~4095
        for address in range(first,last,4096):
            if address not in mapped:cpu.mem_map(address,4096);mapped.add(address)
        if segment['data']:cpu.mem_write(segment['address'],segment['data'])
    cpu.mem_map(src,mapped_size(len(values)))
    cpu.mem_map(dst,mapped_size(12*n+16))
    cpu.mem_map(stack,65536)
    cpu.mem_map(sentinel,4096)
    if values:cpu.mem_write(src,bytes(values))
    guard=struct.pack('<ff',12345.0,-54321.0)
    cpu.mem_write(dst+12*n,guard)
    if machine==62:
        cpu.reg_write(xr.UC_X86_REG_RDI,src if n else 0)
        cpu.reg_write(xr.UC_X86_REG_RSI,dst if n else 0)
        cpu.reg_write(xr.UC_X86_REG_RDX,n)
        cpu.reg_write(xr.UC_X86_REG_MXCSR,0x1f80)
        sp=stack+65536-8
        cpu.mem_write(sp,struct.pack('<Q',sentinel))
        cpu.reg_write(xr.UC_X86_REG_RSP,sp)
        pc=xr.UC_X86_REG_RIP
    else:
        cpu.reg_write(ar.UC_ARM64_REG_CPACR_EL1,3<<20)
        cpu.reg_write(ar.UC_ARM64_REG_FPCR,0)
        cpu.reg_write(ar.UC_ARM64_REG_X0,src if n else 0)
        cpu.reg_write(ar.UC_ARM64_REG_X1,dst if n else 0)
        cpu.reg_write(ar.UC_ARM64_REG_X2,n)
        cpu.reg_write(ar.UC_ARM64_REG_SP,stack+65536-16)
        cpu.reg_write(ar.UC_ARM64_REG_X30,sentinel)
        pc=ar.UC_ARM64_REG_PC
    cpu.emu_start(function['address'],sentinel,count=max(1000,n*100+1000))
    assert cpu.reg_read(pc)==sentinel,'Function did not return within instruction limit'
    actual=bytes(cpu.mem_read(dst,12*n))
    expected=b''.join(struct.pack('<f',values[3*i+channel]/255.0) for channel in (2,1,0) for i in range(n))
    assert actual==expected,'FP32 output differs from independent reference'
    assert bytes(cpu.mem_read(dst+12*n,8))==guard,'Output guard changed'
    return {'pixels':n,'checked_values':3*n,'passed':True,'output_sha256':hashlib.sha256(actual).hexdigest()}

def main():
    rng=random.Random(662)
    cases=[('zero_count',[]),('one_pixel',[0,127,255]),('two_pixels_channel_order',[0,127,255,255,0,128]),('all_byte_values',[v for v in range(256) for _ in range(3)]),('odd_length_random',[rng.randrange(256) for _ in range(51)]),('640x640_random',[rng.randrange(256) for _ in range(3*640*640)])]
    results=[]
    (ROOT/'disassembly').mkdir(exist_ok=True)
    for name in ('x86_64','armv8_aarch64'):
        path=ROOT/f'verification/preprocess_{name}.elf'
        machine,segments,function=read_elf(path)
        decoder=capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64) if machine==62 else capstone.Cs(capstone.CS_ARCH_ARM64,capstone.CS_MODE_ARM)
        instructions=list(decoder.disasm(function['data'],function['address']))
        assert sum(i.size for i in instructions)==function['size']
        disassembly='\n'.join(f'{i.address:016x}  {i.bytes.hex():<22}  {i.mnemonic:<10} {i.op_str}' for i in instructions)+'\n'
        (ROOT/f'disassembly/preprocess_{name}.txt').write_text(disassembly,encoding='utf-8')
        tested=[{'name':label,**execute(machine,segments,function,values)} for label,values in cases]
        results.append({'target':name,'elf_machine':machine,'assembly_sha256':hashlib.sha256((ROOT/f'assembly/preprocess_{name}.s').read_bytes()).hexdigest(),'object_sha256':hashlib.sha256((ROOT/f'objects/preprocess_{name}.o').read_bytes()).hexdigest(),'elf_sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'function_bytes':function['size'],'static_instruction_count':len(instructions),'instruction_sizes_bytes':sorted({i.size for i in instructions}),'cases':tested})
    assert [c['output_sha256'] for c in results[0]['cases']]==[c['output_sha256'] for c in results[1]['cases']]
    result={'passed':True,'method':'Unicorn instruction emulation of ELF files assembled from the submitted .s files; no hardware performance measurement','unicorn_version':unicorn.__version__,'capstone_version':capstone.__version__,'targets':results}
    (ROOT/'verification/assembly_tests.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'passed':True,'targets':[{k:t[k] for k in ('target','function_bytes','static_instruction_count','instruction_sizes_bytes')} for t in results],'test_cases_per_target':len(cases)},indent=2))

if __name__=='__main__':main()
