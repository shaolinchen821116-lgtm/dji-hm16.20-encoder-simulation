"""Decode, inspect actual coding tools, and compare independent reconstructions."""
from pathlib import Path
from collections import Counter
import subprocess,os,json,hashlib,re,csv,argparse
from run_encode import ROOT,NAME

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for data in iter(lambda:f.read(1024*1024),b''):h.update(data)
    return h.hexdigest()

def run(intra8_tu4=False):
    output=ROOT/'output'
    if intra8_tu4:output=output/'intra8_tu4'
    stream=output/(NAME+'.265');stats=output/'decoded_tools.jsonl'
    env=os.environ.copy();env['POCKET_STATS_FILE']=str(stats);env.pop('VSA_TRACE_DIR',None)
    with (output/'decoder.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(ROOT/'bin/TAppDecoder_pocket4.exe'),'-b',str(stream),'-o',str(output/'hm_decoded8.yuv'),'--SEIDecodedPictureHash=1','--OutputBitDepth=8'],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    frames=[json.loads(line) for line in stats.read_text().splitlines()]
    assert len(frames)==20 and [f['poc'] for f in frames]==list(range(20))
    assert Counter(f['type'] for f in frames)=={'I':1,'P':19}
    hist={};totals=Counter()
    expected={'coded_width':1920,'coded_height':1080,'crop_left':0,'crop_right':0,'crop_top':0,'crop_bottom':0,'cabac_init_present':0,'bitdepth':8,'ctu_size':32,'min_cu':8,'max_cu':32,'min_tu':4,'max_tu':16,'syntax_intra_transform_depth':1 if intra8_tu4 else 0,'syntax_inter_transform_depth':2,'amp':0,'tmvp_sps':1,'ts_allowed':0,'sao':1,'strong_intra_smoothing':0,'pcm':0,'tiles':0,'wpp':0,'deblocking_control_present':0,'deblocking_disabled':0,'sign_hiding':1,'weighted_pred_p':0,'weighted_pred_b':0,'dqp_enabled':1,'qg_size':16,'max_merge_candidates':5,'slice_qp':27}
    for f in frames:
        for key,value in expected.items():assert f[key]==value,(f['poc'],key,f[key],value)
        if f['type']=='P':
            assert f['l0_refs']==1 and f['l1_refs']==0 and f['tmvp_slice']==1
            assert f['histograms'].get('bottom_visible_cu_mode',{}).get('0',0)>0, 'No inter CU in bottom visible strip'
        if f['type']=='I':assert f['nal_type']==20
        assert f['transform_skip_tus']==0
        h=f['histograms']
        assert set(h.get('intra_cu_size',{}))<={'8','16'}
        assert set(h.get('inter_cu_size',{}))<={'8','16'}
        assert set(h.get('intra_pu_width',{}))<={'8','16'}
        assert set(h['pu_partition'])<={'0','1','2'}
        assert set(h['luma_tu_size'])<=({'4','8','16'} if intra8_tu4 else {'8','16'})
        assert set(h.get('inter_luma_tu_size',{}))<={'8','16'}
        assert set(h.get('intra_cu16_luma_tu_size',{}))<={'16'}
        assert set(h['rqt_depth'])<={'0','1'}
        assert set(h.get('intra_chroma_mode',{}))<={'36'}
        assert set(h['cu_qp'])=={'27'}
        if not intra8_tu4:assert h.get('intra_cu_size',{})==h.get('intra_luma_tu_size',{})
        else:
            leaves=h.get('intra_cu8_luma_tu_leaves_per_cu',{});tu=h.get('intra_cu8_luma_tu_size',{})
            assert set(leaves)<={'1','4'}
            assert sum(leaves.values())==h.get('intra_cu_size',{}).get('8',0)
            assert tu.get('4',0)==4*leaves.get('4',0) and tu.get('8',0)==leaves.get('1',0)
            assert h.get('intra_cu16_luma_tu_size',{}).get('16',0)==h.get('intra_cu_size',{}).get('16',0)
        for key,values in h.items():hist.setdefault(key,Counter()).update(values)
        for key in ('skip_cus','merge_pus','amvp_pus','luma_cbf_tus','transform_skip_tus'):totals[key]+=f[key]
    # All retained tools must be covered by the ParkScene test, not just allowed.
    assert set(hist['intra_cu_size'])=={'8','16'}
    assert set(hist['inter_cu_size'])=={'8','16'}, 'Both inter CU8 and CU16 must be covered'
    assert set(hist.get('inter_pu8x8_cu_size',{}))<={'8'}
    assert set(hist['pu_partition'])=={'0','1','2'}
    assert set(hist['luma_tu_size'])==({'4','8','16'} if intra8_tu4 else {'8','16'})
    if intra8_tu4:assert hist.get('intra_cu8_cbf_luma_tu_size',{}).get('4',0)>0, 'No nonzero intra CU8 TU4 was covered'
    assert totals['amvp_pus'] and totals['merge_pus'] and totals['skip_cus']
    log=(output/'decoder.log').read_text()
    assert log.count('(OK)')==20 and '***ERROR***' not in log
    ffmpeg=r'C:\ffmpeg\bin\ffmpeg.exe';ffprobe=r'C:\ffmpeg\bin\ffprobe.exe'
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-count_frames','-show_streams','-show_frames','-of','json',str(stream)],text=True))
    (output/'ffprobe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
    info=probe['streams'][0]
    assert (info['width'],info['height'],info['pix_fmt'],info['profile'])==(1920,1080,'yuv420p','Main')
    assert int(info['nb_read_frames'])==20 and info['r_frame_rate']=='24/1'
    with (output/'ffmpeg_decode.log').open('w',encoding='utf-8') as log:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(stream),'-pix_fmt','yuv420p','-f','rawvideo','-y',str(output/'ffmpeg_decoded8.yuv')],stdout=log,stderr=subprocess.STDOUT,check=True)
    hashes={p.name:sha(p) for p in [output/(NAME+'_recon8.yuv'),output/'hm_decoded8.yuv',output/'ffmpeg_decoded8.yuv']}
    assert len(set(hashes.values()))==1,hashes
    expected_size=1920*1080*3//2*20
    for name in hashes:assert (output/name).stat().st_size==expected_size
    with (output/'headers_trace.log').open('w',encoding='utf-8') as log:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','info','-i',str(stream),'-map','0:v:0','-c:v','copy','-bsf:v','trace_headers','-frames:v','1','-f','null','-'],stdout=log,stderr=subprocess.STDOUT,check=True)
    encoder=(output/'encoder.log').read_text()
    pictures=re.findall(r'POC\s+(\d+).*?\( ([IPB])-SLICE, nQP (\d+) QP (\d+) \)\s+(\d+) bits \[Y\s+([\d.]+) dB\s+U\s+([\d.]+) dB\s+V\s+([\d.]+) dB\]',encoder)
    assert len(pictures)==20 and all(p[2]=='27' and p[3]=='27' for p in pictures)
    with (output/'picture_results.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['POC','Type','NominalQP','SliceQP','Bits','Y_PSNR_dB','U_PSNR_dB','V_PSNR_dB']);writer.writerows(pictures)
    run=json.loads((output/'encode_run.json').read_text())
    psnr={c:sum(float(p[i]) for p in pictures)/20 for c,i in [('Y',5),('U',6),('V',7)]}
    report={'passed':True,'intra8_tu4_extension':intra8_tu4,'frames':20,'types':dict(Counter(f['type'] for f in frames)),'qp':27,'width':1920,'height':1080,'fps':24,'profile':info['profile'],'level':info['level'],'pixel_format':info['pix_fmt'],'bitstream_bytes':stream.stat().st_size,'bitrate_kbps_including_headers':stream.stat().st_size*8*24/20/1000,'encoder_picture_bitrate_kbps':sum(int(p[4]) for p in pictures)*24/20/1000,'mean_picture_psnr_db':psnr,'encode_seconds':run['elapsed_seconds'],'md5_sei_ok_frames':20,'encoder_hm_ffmpeg_reconstruction_exact_match':True,'reconstruction_sha256':hashes,'headers_checked':expected,'histograms':hist,'totals':dict(totals),'bitstream_sha256':sha(stream),'encoder_sha256':sha(ROOT/'bin/TAppEncoder_pocket4.exe'),'decoder_sha256':sha(ROOT/'bin/TAppDecoder_pocket4.exe')}
    (output/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (output/'supported_configuration.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['Metric','Configured_or_Allowed','Observed','Verification'])
        for key,value in expected.items():writer.writerow([key,value,sorted(set(str(p[key]) for p in frames)),'Passed'])
        for key in ['intra_cu_size','inter_cu_size','intra_pu_width','luma_tu_size','rqt_depth','pu_partition','intra_chroma_mode','cu_qp']:
            writer.writerow([key,'Pocket4 observed subset',json.dumps(hist.get(key,{})),'Passed'])
    print(json.dumps({k:v for k,v in report.items() if k not in ('histograms','headers_checked')},indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--intra8-tu4',action='store_true');args=parser.parse_args();run(args.intra8_tu4)
