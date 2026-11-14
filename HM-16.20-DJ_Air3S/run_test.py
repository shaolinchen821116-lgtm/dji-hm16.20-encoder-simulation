"""Standalone 8-bit ParkScene experiment and independent reconstruction checks."""
from pathlib import Path
from collections import Counter
import json,subprocess,os,hashlib,time,re,csv,argparse,shutil
ROOT=Path(__file__).resolve().parent
INPUT=Path(r'D:\yuv_data\yuv_hevc\ClassB\ParkScene_1920x1080_24.yuv')

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(1024*1024),b''):h.update(block)
    return h.hexdigest()

def run(verify_only=False):
    p=json.loads((ROOT/'camera_policy.json').read_text());name=p['camera']
    out=ROOT/'output';out.mkdir(exist_ok=True)
    stream=out/f'ParkScene_1920x1080_24_{name}_qp27_20f.265';recon=out/'encoder_recon8.yuv'
    config=ROOT/'cfg/camera_main8_qp27.cfg';enc=ROOT/'bin/TAppEncoder_camera.exe';dec=ROOT/'bin/TAppDecoder_camera.exe'
    resultfile=out/'verification.json'
    if resultfile.exists():resultfile.unlink()
    env=os.environ.copy();env.pop('VSA_TRACE_DIR',None);env.pop('POCKET_STATS_FILE',None);env['CAMERA_STATS_FAST']='1'
    if not verify_only:
        start=time.perf_counter()
        command=[str(enc),'-c',str(config),'-i',str(INPUT),'-b',str(stream),'-o',str(recon)]
        with (out/'encoder.log').open('w',encoding='utf-8') as log:
            subprocess.run(command,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (out/'encode_run.json').write_text(json.dumps({'command':command,'elapsed_seconds':time.perf_counter()-start,'input':str(INPUT),'frames':20,'qp':27,'input_bitdepth':8,'internal_bitdepth':8},indent=2))
    env['POCKET_STATS_FILE']=str(out/'decoded_tools.jsonl')
    with (out/'decoder.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(dec),'-b',str(stream),'-o',str(out/'hm_decoded8.yuv'),'--SEIDecodedPictureHash=1'],cwd=ROOT,stdout=log,stderr=subprocess.STDOUT,env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    frames=[json.loads(line) for line in (out/'decoded_tools.jsonl').read_text().splitlines()]
    assert len(frames)==20 and [f['poc'] for f in frames]==list(range(20))
    assert Counter(f['type'] for f in frames)=={'I':1,'P':19}
    hist={}
    expected={'coded_width':1920,'coded_height':1080+p['pad'],'crop_bottom':p['pad'],'bitdepth':8,'ctu_size':p['ctu'],'min_cu':8,'max_cu':p['ctu'],'min_tu':4,'max_tu':p['max_tu'],'syntax_intra_transform_depth':p['intra_depth']-1,'syntax_inter_transform_depth':p['inter_depth']-1,'amp':p['amp'],'tmvp_sps':p['tmvp'],'ts_allowed':0,'sao':1,'strong_intra_smoothing':0,'pcm':0,'tiles':int(p['tile_cols']>1),'tile_cols':p['tile_cols'],'tile_rows':1,'wpp':0,'sign_hiding':p['sign_hiding'],'weighted_pred_p':0,'weighted_pred_b':0,'dqp_enabled':1,'qg_size':p['ctu']>>p['dqp_depth'],'slice_qp':27,'cabac_init_present':p['cabac'],'beta_offset':p['beta'],'tc_offset':p['tc']}
    for f in frames:
        for key,value in expected.items():assert f[key]==value,(f['poc'],key,f[key],value)
        if f['type']=='P':assert f['l0_refs']==1 and f['l1_refs']==0 and f['max_merge_candidates']==p['merge']
        else:assert f['nal_type']==p['idr'],(f['nal_type'],p['idr'])
        h=f['histograms']
        assert set(map(int,h.get('intra_cu_size',{})))<=set(p['intra_sizes'])
        assert set(map(int,h.get('inter_cu_size',{})))<=set(p['inter_sizes'])
        assert set(h['cu_qp'])=={'27'} and f['transform_skip_tus']==0
        assert set(map(int,h.get('inter_luma_tu_size',{})))<=set(2**v for v in range(p['min_inter_tu'].bit_length()-1,p['max_inter_tu'].bit_length()))
        if not p['amp']:assert all(int(k)<4 for k in h['pu_partition'])
        if not p['intra_nxn']:assert '4' not in h.get('intra_pu_width',{})
        if p['dm_only']:assert set(h.get('intra_chroma_mode',{}))<={'36'}
        # Every final intra CU/TU relationship must match the camera policy.
        for key in h.get('intra_cu_tu_pairs',{}):
            cu,tu=divmod(int(key),1024)
            assert tu==cu or (p['intra_nxn'] and cu==8 and tu==4),(cu,tu)
        for key,items in h.items():hist.setdefault(key,Counter()).update(items)
    decoderlog=(out/'decoder.log').read_text()
    assert decoderlog.count('(OK)')==20 and '***ERROR***' not in decoderlog
    ffmpeg=shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe';ffprobe=shutil.which('ffprobe') or r'C:\ffmpeg\bin\ffprobe.exe'
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-show_streams','-of','json',str(stream)],text=True))
    (out/'ffprobe.json').write_text(json.dumps(probe,indent=2));info=probe['streams'][0]
    assert (info['width'],info['height'],info['pix_fmt'],info['profile'],int(info['nb_read_frames']))==(1920,1080,'yuv420p','Main',20)
    assert info['r_frame_rate']=='24/1'
    with (out/'ffmpeg_decode.log').open('w') as log:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(stream),'-pix_fmt','yuv420p','-f','rawvideo','-y',str(out/'ffmpeg_decoded8.yuv')],stdout=log,stderr=subprocess.STDOUT,check=True)
    hashes={q.name:sha(q) for q in (recon,out/'hm_decoded8.yuv',out/'ffmpeg_decoded8.yuv')}
    assert len(set(hashes.values()))==1,hashes
    assert all((out/q).stat().st_size==62208000 for q in hashes)
    trace=subprocess.run([ffmpeg,'-hide_banner','-loglevel','info','-i',str(stream),'-c:v','copy','-bsf:v','trace_headers','-frames:v','1','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',check=True).stdout
    (out/'headers_trace.log').write_text(trace);fields={}
    for line in trace.splitlines():
        match=re.search(r']\s+\d+\s+(\w+(?:\[\d+\])?)\s+[01]+\s+=\s+(-?\d+)\s*$',line)
        if match:fields[match[1]]=int(match[2])
    assert fields['deblocking_filter_control_present_flag']==int(bool(p['deblock_override'] or p['beta'] or p['tc']))
    assert fields.get('deblocking_filter_override_enabled_flag',0)==p['deblock_override']
    encodetext=(out/'encoder.log').read_text()
    pictures=re.findall(r'POC\s+(\d+).*?\( ([IPB])-SLICE, nQP (\d+) QP (\d+) \)\s+(\d+) bits \[Y\s+([\d.]+) dB\s+U\s+([\d.]+) dB\s+V\s+([\d.]+) dB\]',encodetext)
    assert len(pictures)==20
    with (out/'picture_results.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['POC','Type','NominalQP','SliceQP','Bits','Y_PSNR_dB','U_PSNR_dB','V_PSNR_dB']);w.writerows(pictures)
    report={'passed':True,'camera':name,'frames':20,'qp':27,'source_profile':'Main10','test_profile':'Main / 8-bit','width':1920,'height':1080,'coded_height':1080+p['pad'],'fps':24,'types':dict(Counter(f['type'] for f in frames)),'bitstream_bytes':stream.stat().st_size,'bitrate_kbps':stream.stat().st_size*8*24/20/1000,'mean_psnr_db':{c:sum(float(row[i]) for row in pictures)/20 for c,i in [('Y',5),('U',6),('V',7)]},'encoder_hm_ffmpeg_exact_match':True,'md5_sei_ok_frames':20,'reconstruction_sha256':hashes,'expected_fields':expected,'observed_histograms':hist,'encoder_sha256':sha(enc),'decoder_sha256':sha(dec),'bitstream_sha256':sha(stream),'config_sha256':sha(config),'encode_seconds':json.loads((out/'encode_run.json').read_text())['elapsed_seconds'],'coverage':{'intra4':bool(hist.get('intra_pu_width',{}).get('4')),'amp':any(int(k)>=4 for k in hist['pu_partition']),'inter8':bool(hist.get('inter_cu_size',{}).get('8')),'intra32':bool(hist.get('intra_cu_size',{}).get('32')),'inter32':bool(hist.get('inter_cu_size',{}).get('32'))}}
    resultfile.write_text(json.dumps(report,indent=2));print(json.dumps({k:v for k,v in report.items() if k not in ('observed_histograms','expected_fields','reconstruction_sha256')},indent=2),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify-only',action='store_true');run(parser.parse_args().verify_only)
