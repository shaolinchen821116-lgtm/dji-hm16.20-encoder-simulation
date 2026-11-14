"""Regression: compare actual modes in the last 8 visible rows before/after."""
from pathlib import Path
import json,subprocess,os,csv
from run_encode import ROOT

def summarize(frames):
    rows=[]
    for f in frames:
        if f['type']!='P':continue
        h=f['histograms'];mode=h.get('bottom_visible_cu_mode',{})
        intra=h.get('bottom_visible_intra_cu_size',{});inter=h.get('bottom_visible_inter_cu_size',{})
        intra_width=sum(int(size)*count for size,count in intra.items())
        inter_width=sum(int(size)*count for size,count in inter.items())
        assert intra_width+inter_width==1920,(f['poc'],intra,inter)
        rows.append({'poc':f['poc'],'intra_cus':mode.get('1',0),'inter_cus':mode.get('0',0),'intra_luma_columns':intra_width,'inter_luma_columns':inter_width})
    return rows

def run():
    folder=ROOT/'output/border_fix';folder.mkdir(exist_ok=True)
    env=os.environ.copy();env['POCKET_STATS_FILE']=str(folder/'before_tools.jsonl');env.pop('VSA_TRACE_DIR',None)
    with (folder/'before_decoder.log').open('w',encoding='utf-8') as log:
        subprocess.run([str(ROOT/'bin/TAppDecoder_pocket4.exe'),'-b',str(folder/'before_fix.265'),'--SEIDecodedPictureHash=1'],env=env,stdout=log,stderr=subprocess.STDOUT,check=True,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    before_frames=[json.loads(s) for s in (folder/'before_tools.jsonl').read_text().splitlines()]
    after_frames=[json.loads(s) for s in (ROOT/'output/decoded_tools.jsonl').read_text().splitlines()]
    before=summarize(before_frames);after=summarize(after_frames)
    assert len(before)==len(after)==19
    assert all(r['intra_luma_columns']==1920 and r['inter_cus']==0 for r in before)
    assert all(r['inter_cus']>0 for r in after),'A P picture still has an all-intra bottom strip'
    assert all(f['coded_width']==1920 and f['coded_height']==1080 and f['crop_bottom']==0 for f in after_frames)
    assert all(set(f['histograms'].get('inter_cu_size',{}))<={'8','16'} for f in after_frames)
    def totals(rows):
        d={key:sum(r[key] for r in rows) for key in ('intra_cus','inter_cus','intra_luma_columns','inter_luma_columns')}
        d['inter_visible_area_percent']=100*d['inter_luma_columns']/(1920*len(rows));return d
    report={'passed':True,'p_pictures':19,'visible_region':'x=0..1919, y=1072..1079','before':totals(before),'after':totals(after),'per_picture':{'before':before,'after':after},'policy':'Enable CU8/CU16 inter; preserve native coded/display height 1080 and allow boundary CU8 RDO; all modes compete by RD cost.'}
    with (folder/'bottom_row_comparison.csv').open('w',newline='',encoding='utf-8') as f:
        writer=csv.writer(f);writer.writerow(['POC','BeforeIntraCU','BeforeInterCU','AfterIntraCU','AfterInterCU','AfterInterVisibleColumns','AfterIntraVisibleColumns'])
        for b,a in zip(before,after):writer.writerow([a['poc'],b['intra_cus'],b['inter_cus'],a['intra_cus'],a['inter_cus'],a['inter_luma_columns'],a['intra_luma_columns']])
    (folder/'border_verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='per_picture'},indent=2))

if __name__=='__main__':run()
