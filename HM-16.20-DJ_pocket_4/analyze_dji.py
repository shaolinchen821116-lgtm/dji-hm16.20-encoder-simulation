"""Read all DJI pictures; distinguish CU size, PU geometry and CU8 TU leaves."""
from pathlib import Path
from collections import Counter
import subprocess,os,json,hashlib,csv
ROOT=Path(__file__).resolve().parent
SOURCE=Path(r'C:\Users\shaol\Downloads\DJI_20260429163710_0019_D.MP4')

def run():
    folder=ROOT/'source_analysis';folder.mkdir(exist_ok=True)
    ffmpeg=r'C:\ffmpeg\bin\ffmpeg.exe';ffprobe=r'C:\ffmpeg\bin\ffprobe.exe'
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-select_streams','v:0','-show_streams','-of','json',str(SOURCE)],text=True))
    (folder/'ffprobe.json').write_text(json.dumps(probe,indent=2),encoding='utf-8')
    with (folder/'extract.log').open('w',encoding='utf-8') as log:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(SOURCE),'-map','0:v:0','-c:v','copy','-bsf:v','hevc_mp4toannexb','-an','-sn','-dn','-f','hevc','-y',str(folder/'dji_source.265')],stdout=log,stderr=subprocess.STDOUT,check=True)
    env=os.environ.copy();env['POCKET_STATS_FILE']=str(folder/'tools_all_frames.jsonl');env.pop('VSA_TRACE_DIR',None)
    with (folder/'decoder.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(ROOT/'bin/TAppDecoder_pocket4.exe'),'-b',str(folder/'dji_source.265'),'--SEIDecodedPictureHash=1'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    frames=[json.loads(s) for s in (folder/'tools_all_frames.jsonl').read_text().splitlines()]
    assert len(frames)==int(probe['streams'][0]['nb_frames'])
    hist={}
    for frame in frames:
        for key,counts in frame['histograms'].items():hist.setdefault(key,Counter()).update(counts)
    inter8=hist.get('inter_cu_size',{}).get('8',0)
    intra8tu4=hist.get('intra_cu8_luma_tu_size',{}).get('4',0)
    inter_dims={f'{int(k)//1024}x{int(k)%1024}':v for k,v in hist.get('inter_pu_dimensions',{}).items()}
    report={'source':str(SOURCE),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'pictures_decoded':len(frames),'frame_types':dict(Counter(f['type'] for f in frames)),'inter_cu_sizes':hist.get('inter_cu_size',{}),'inter_pu_dimensions':inter_dims,'inter_pu8x8_parent_cu_sizes':hist.get('inter_pu8x8_cu_size',{}),'actual_inter_cu8_count':inter8,'actual_inter_pu8x8_count':sum(hist.get('inter_pu8x8_cu_size',{}).values()),'intra_cu8_count':hist.get('intra_cu_size',{}).get('8',0),'intra_cu8_luma_tu_sizes':hist.get('intra_cu8_luma_tu_size',{}),'intra_cu8_nonzero_luma_tu_sizes':hist.get('intra_cu8_cbf_luma_tu_size',{}),'intra_cu8_luma_tu_leaves_per_cu':hist.get('intra_cu8_luma_tu_leaves_per_cu',{}),'intra_cu8_pu_partition':hist.get('intra_cu8_pu_partition',{}),'actual_intra_cu8_tu4_count':intra8tu4,'sps_intra_depth_syntax_values':sorted(set(f['syntax_intra_transform_depth'] for f in frames)),'sps_inter_depth_syntax_values':sorted(set(f['syntax_inter_transform_depth'] for f in frames)),'sps_min_cu_values':sorted(set(f['min_cu'] for f in frames)),'all_histograms':hist}
    (folder/'source_findings.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (folder/'cu8_tu_and_inter_per_picture.csv').open('w',newline='',encoding='utf-8') as f:
        w=csv.writer(f);w.writerow(['POC','Type','InterCU8','InterCU16','IntraCU8','IntraCU8_TU4','IntraCU8_TU8','SyntaxIntraTransformDepth'])
        for p in frames:
            h=p['histograms'];w.writerow([p['poc'],p['type'],h.get('inter_cu_size',{}).get('8',0),h.get('inter_cu_size',{}).get('16',0),h.get('intra_cu_size',{}).get('8',0),h.get('intra_cu8_luma_tu_size',{}).get('4',0),h.get('intra_cu8_luma_tu_size',{}).get('8',0),p['syntax_intra_transform_depth']])
    with (folder/'headers_trace.log').open('w',encoding='utf-8') as log:
        subprocess.run([ffmpeg,'-hide_banner','-loglevel','info','-i',str(folder/'dji_source.265'),'-c:v','copy','-bsf:v','trace_headers','-frames:v','1','-f','null','-'],stdout=log,stderr=subprocess.STDOUT,check=True)
    print(json.dumps({k:v for k,v in report.items() if k!='all_histograms'},indent=2))

if __name__=='__main__':run()
