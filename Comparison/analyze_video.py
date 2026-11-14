"""Portable complete-clip HEVC tool analysis using a supplied stats decoder."""
from pathlib import Path
from collections import Counter
import argparse,subprocess,shutil,os,json,hashlib,re

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input',required=True,type=Path)
    parser.add_argument('--decoder',required=True,type=Path,help='A built Action6/Air3S/Mavic3 stats decoder')
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args();source=args.input.resolve();decoder=args.decoder.resolve();out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    ffprobe=shutil.which('ffprobe') or r'C:\ffmpeg\bin\ffprobe.exe';ffmpeg=shutil.which('ffmpeg') or r'C:\ffmpeg\bin\ffmpeg.exe'
    probe=json.loads(subprocess.check_output([ffprobe,'-v','error','-select_streams','v:0','-show_streams','-of','json',str(source)],text=True))
    if not probe['streams'] or probe['streams'][0]['codec_name']!='hevc':raise ValueError('Input must contain HEVC video')
    (out/'ffprobe.json').write_text(json.dumps(probe,indent=2))
    subprocess.run([ffmpeg,'-hide_banner','-loglevel','error','-i',str(source),'-map','0:v:0','-c:v','copy','-bsf:v','hevc_mp4toannexb','-an','-sn','-dn','-f','hevc','-y',str(out/'source.265')],check=True)
    env=os.environ.copy();env['POCKET_STATS_FILE']=str(out/'tools_all_frames.jsonl');env['CAMERA_STATS_FAST']='1';env.pop('VSA_TRACE_DIR',None)
    with (out/'decoder.log').open('w') as log:
        subprocess.run([str(decoder),'-b',str(out/'source.265')],stdout=log,stderr=subprocess.STDOUT,env=env,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    hist={};values={};types=Counter();ipos=[];n=0
    for i,line in enumerate((out/'tools_all_frames.jsonl').open()):
        f=json.loads(line);n+=1;types[f['type']]+=1
        if f['type']=='I':ipos.append(i)
        for key,value in f.items():
            if key not in ('poc','histograms','ref_pocs') and isinstance(value,(int,str)):values.setdefault(key,set()).add(value)
        for key,value in f['histograms'].items():hist.setdefault(key,Counter()).update(value)
    if not n:raise ValueError('Decoder produced no picture statistics')
    expected=probe['streams'][0].get('nb_frames')
    if expected and expected!='N/A' and n!=int(expected):raise ValueError(f'Incomplete decode: {n}/{expected}')
    fields={}
    trace=subprocess.run([ffmpeg,'-hide_banner','-loglevel','info','-i',str(out/'source.265'),'-c:v','copy','-bsf:v','trace_headers','-frames:v','1','-f','null','-'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='replace',check=True).stdout
    (out/'headers_trace.log').write_text(trace)
    for line in trace.splitlines():
        m=re.search(r']\s+\d+\s+(\w+(?:\[\d+\])?)\s+[01]+\s+=\s+(-?\d+)\s*$',line)
        if m:fields[m[1]]=int(m[2])
    result={'complete':True,'source':str(source),'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'pictures_decoded':n,'stream':probe['streams'][0],'frame_types':types,'i_decode_positions':ipos,'i_intervals':dict(Counter(b-a for a,b in zip(ipos,ipos[1:]))),'frame_values':{k:sorted(v) for k,v in values.items()},'histograms':hist,'headers_first_picture':fields}
    (out/'analysis.json').write_text(json.dumps(result,indent=2));print(f'Complete: {n} pictures. {out / "analysis.json"}')

if __name__=='__main__':main()
