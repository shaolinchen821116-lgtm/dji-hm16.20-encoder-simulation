"""Exercise a complete IDR cycle with 65 small frames, using the actual encoder."""
from pathlib import Path
import subprocess,os,json
ROOT=Path(__file__).resolve().parent

def main():
    policy=ROOT/'camera_policy.json'
    if policy.exists():
        p=json.loads(policy.read_text());camera=p['camera'];period=p['period'];idr=p['idr'];config=ROOT/'cfg/camera_main8_qp27.cfg';enc=ROOT/'bin/TAppEncoder_camera.exe';dec=ROOT/'bin/TAppDecoder_camera.exe'
    else:
        camera='Pocket4';period=30;idr=20;config=ROOT/'cfg/pocket4_main8_qp27.cfg';enc=ROOT/'bin/TAppEncoder_pocket4.exe';dec=ROOT/'bin/TAppDecoder_pocket4.exe'
    out=ROOT/'output/gop_probe';out.mkdir(parents=True,exist_ok=True)
    with (out/'input64.yuv').open('wb') as f:
        for frame in range(65):
            f.write(bytes(16+((x*2+y+frame)%180) for y in range(64) for x in range(64)));f.write(bytes([120+frame%12])*1024);f.write(bytes([132-frame%12])*1024)
    env=os.environ.copy();env.pop('VSA_TRACE_DIR',None);env.pop('POCKET_STATS_FILE',None);env['CAMERA_STATS_FAST']='1'
    with (out/'encoder.log').open('w') as log:
        subprocess.run([str(enc),'-c',str(config),'-i',str(out/'input64.yuv'),'-b',str(out/'probe.265'),'-o',str(out/'recon.yuv'),'--SourceWidth=64','--SourceHeight=64','--FramesToBeEncoded=65','--ConformanceWindowMode=1','--VerticalPadding=0','--HorizontalPadding=0'],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    env['POCKET_STATS_FILE']=str(out/'tools.jsonl')
    with (out/'decoder.log').open('w') as log:
        subprocess.run([str(dec),'-b',str(out/'probe.265'),'--SEIDecodedPictureHash=1'],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    frames=[json.loads(line) for line in (out/'tools.jsonl').read_text().splitlines()]
    positions=[i for i,f in enumerate(frames) if f['type']=='I']
    assert len(frames)==65 and positions==list(range(0,65,period)),positions
    assert all(f['nal_type']==idr for f in frames if f['type']=='I')
    assert all(f['l0_refs']==1 and f['l1_refs']==0 for f in frames if f['type']=='P')
    assert all(f['tiles']==0 and f['wpp']==0 for f in frames)
    log=(out/'decoder.log').read_text();assert log.count('(OK)')==65 and '***ERROR***' not in log
    report={'passed':True,'camera':camera,'frames':65,'width':64,'height':64,'i_interval':period,'i_decode_indices':positions,'idr_nal_type':idr,'md5_sei_ok_frames':65,'single_active_l0_for_all_p':True,'tiles':0}
    (out/'verification.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':main()
