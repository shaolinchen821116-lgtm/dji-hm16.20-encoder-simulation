"""Encode the requested ParkScene frames. Paths are relative to this experiment."""
from pathlib import Path
import subprocess,time,json,hashlib,os,argparse

ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'D:\yuv_data\yuv_hevc\ClassB\ParkScene_1920x1080_24.yuv')
NAME='ParkScene_1920x1080_24_pocket4_qp27_20f'

def run(intra8_tu4=False):
    output=ROOT/'output'
    if intra8_tu4:output=output/'intra8_tu4'
    output.mkdir(parents=True,exist_ok=True)
    config=ROOT/('cfg/pocket4_main8_intra8_tu4_qp27.cfg' if intra8_tu4 else 'cfg/pocket4_main8_qp27.cfg')
    required=1920*1080*3//2*20
    if SOURCE.stat().st_size<required:raise RuntimeError('Input sequence is shorter than 20 8-bit YUV420 frames.')
    command=[str(ROOT/'bin/TAppEncoder_pocket4.exe'),'-c',str(config),'-i',str(SOURCE),'-b',str(output/(NAME+'.265')),'-o',str(output/(NAME+'_recon8.yuv'))]
    start=time.perf_counter()
    env=os.environ.copy();env.pop('VSA_TRACE_DIR',None);env.pop('POCKET_STATS_FILE',None)
    with (output/'encoder.log').open('w',encoding='utf-8') as log:
        result=subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    elapsed=time.perf_counter()-start
    meta={'command':command,'elapsed_seconds':elapsed,'exit_code':result.returncode,'input':str(SOURCE),'input_bitdepth':8,'internal_bitdepth':8,'frames':20,'qp':27,'config_sha256':hashlib.sha256(config.read_bytes()).hexdigest()}
    (output/'encode_run.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
    if result.returncode:raise RuntimeError('Encoder failed. See output/encoder.log')
    if not (output/(NAME+'.265')).stat().st_size:raise RuntimeError('Encoder produced an empty bitstream.')
    print(json.dumps(meta,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--intra8-tu4',action='store_true');args=parser.parse_args();run(args.intra8_tu4)
