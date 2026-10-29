"""Verify exported FP32 reference math and output-plane indexing on Windows."""
import ctypes,hashlib,json,random,struct
from pathlib import Path

ROOT=Path(__file__).resolve().parent
def f32(x):return struct.unpack('<f',struct.pack('<f',x))[0]

def main():
    lib=ctypes.CDLL(str(ROOT/'verification/preprocess_test.dll'))
    fn=lib.yolo_bgr8_to_rgb_chw_f32
    fn.argtypes=[ctypes.POINTER(ctypes.c_ubyte),ctypes.POINTER(ctypes.c_float),ctypes.c_size_t];fn.restype=None
    fn(None,None,0)
    cases=[];rng=random.Random(662)
    arrays=[('one_pixel',[0,127,255]),('two_pixels_channel_order',[0,127,255,255,0,128]),('all_byte_values',[v for v in range(256) for _ in range(3)]),('odd_length_random',[rng.randrange(256) for _ in range(3*17)]),('640x640_random',[rng.randrange(256) for _ in range(3*640*640)])]
    for name,values in arrays:
        n=len(values)//3;src=(ctypes.c_ubyte*len(values))(*values)
        # Guard floats reveal any writes beyond the three output planes.
        out=(ctypes.c_float*(3*n+2))();out[3*n]=12345.0;out[3*n+1]=-54321.0
        fn(src,out,n)
        expected=[f32(values[3*i+channel]/255.0) for channel in (2,1,0) for i in range(n)]
        assert all(out[i]==value for i,value in enumerate(expected)),name
        assert out[3*n]==12345.0 and out[3*n+1]==-54321.0,name
        cases.append({'name':name,'pixels':n,'checked_values':3*n,'passed':True})
    result={'passed':True,'native_test_target':'x86_64 Windows','comparison':'Exact FP32 values vs independent Python index/rounding reference','zero_count_null_pointer_case':True,'cases':cases,'source_sha256':hashlib.sha256((ROOT/'src/preprocess_core.c').read_bytes()).hexdigest()}
    (ROOT/'verification/reference_tests.json').write_text(json.dumps(result,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
