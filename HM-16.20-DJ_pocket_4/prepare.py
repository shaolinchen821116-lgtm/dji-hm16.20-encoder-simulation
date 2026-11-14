"""Prepare a separate HM 16.20 Pocket 4 experiment from the stock source."""
from pathlib import Path
import re,difflib

ROOT=Path(__file__).resolve().parent
HM=ROOT/'HM-16.20'
ORIGINAL=next(p for p in (ROOT.parent/'HM-HM-16.20',ROOT.parent.parent/'HM-HM-16.20') if p.is_dir())

def edit(relative,fn):
    p=HM/relative;s=(ORIGINAL/relative).read_text(encoding="utf-8");p.write_text(fn(s),encoding='utf-8')

def insert_body(s,signature,code):
    pos=s.index('\n{',s.index(signature))+2
    return s[:pos]+'\n  // Pocket 4 observed-tool subset: restrict encoder candidates.\n'+code+s[pos:]

def cu(s):
    s=insert_body(s,'Void TEncCu::xCheckRDCostMerge2Nx2N(', '  if (rpcTempCU->getWidth(0) != 8 && rpcTempCU->getWidth(0) != 16) return;\n')
    # Both AMP_MRG signatures share the body after #endif.
    pos=s.index('\n{',s.index('Void TEncCu::xCheckRDCostInter('))+2
    s=s[:pos]+'\n  // DJI full-clip scan also found rare CU8 inter with one 8x8 PU.\n  const UInt pocketInterSize = rpcTempCU->getWidth(0);\n  if ((pocketInterSize != 8 && pocketInterSize != 16) ||\n      (pocketInterSize == 8 && ePartSize != SIZE_2Nx2N) ||\n      (ePartSize != SIZE_2Nx2N && ePartSize != SIZE_2NxN && ePartSize != SIZE_Nx2N)) return;\n'+s[pos:]
    s=insert_body(s,'Void TEncCu::xCheckRDCostIntra(', '  if ((rpcTempCU->getWidth(0) != 8 && rpcTempCU->getWidth(0) != 16) || eSize != SIZE_2Nx2N) return;\n')
    s=s.replace('        // do normal intra modes','        // Preserve an intra fallback when all searched inter modes are unavailable.\n        const Bool pocketNeedsIntra = rpcBestCU->getTotalCost() == MAX_DOUBLE;\n        // do normal intra modes')
    s=s.replace('if ( m_pcEncCfg->getTMCTSSEITileConstraint() ||','if ( pocketNeedsIntra || m_pcEncCfg->getTMCTSSEITileConstraint() ||')
    s=s.replace('if((rpcBestCU->getSlice()->getSliceType() == I_SLICE)', 'if(pocketNeedsIntra || (rpcBestCU->getSlice()->getSliceType() == I_SLICE)')
    return s

edit('source/Lib/TLibEncoder/TEncCu.cpp',cu)

def search(s):
    old='const Bool bCheckSplit  = ( uiLog2TrSize >  pcCU->getQuadtreeTULog2MinSizeInCU(uiAbsPartIdx) );'
    assert s.count(old)==1
    s=s.replace(old,'// Preserve SPS min-TU4 capability, but do not search luma TU4.\n  const Bool bCheckSplit = (uiLog2TrSize > 3) && (uiLog2TrSize > pcCU->getQuadtreeTULog2MinSizeInCU(uiAbsPartIdx));')
    intra='        Bool    bCheckSplit   = ( uiLog2TrSize  >  pcCU->getQuadtreeTULog2MinSizeInCU(uiAbsPartIdx) );'
    assert s.count(intra)==1
    s=s.replace(intra,intra+'\n  // Optional intra hierarchy depth 2 enables CU8 -> four TU4.\n  // CU16 keeps its single TU16; inter TU4 remains disabled below.\n  if (pcCU->getWidth(0) != 8) bCheckSplit = false;')

    old='pcCU->getAllowedChromaDir( uiPartOffset, uiModeList );'
    assert s.count(old)==1
    s=s.replace(old,old+'\n        // All observed chroma intra PUs use derived mode (DM).\n        uiModeList[0] = DM_CHROMA_IDX;\n        uiMinMode = 0; uiMaxMode = 1;')
    return s
edit('source/Lib/TLibEncoder/TEncSearch.cpp',search)

# HM otherwise omits VUI timing unless HRD/SEI is requested. Signal the
# configured progressive frame rate without enabling HRD rate control.
def timing(s):
    old='    pcVUI->setHrdParametersPresentFlag(false);'
    assert s.count(old)==1
    return s.replace('pps.setCabacInitPresentFlag(CABAC_INIT_PRESENT_FLAG);','pps.setCabacInitPresentFlag(false);').replace(old,old+'\n    // Pocket experiment: explicit progressive timing even without HRD SEI.\n    pcVUI->getTimingInfo()->setTimingInfoPresentFlag(true);\n    pcVUI->getTimingInfo()->setNumUnitsInTick(1);\n    pcVUI->getTimingInfo()->setTimeScale(getFrameRate());')
edit('source/Lib/TLibEncoder/TEncTop.cpp',timing)
edit('source/Lib/TLibEncoder/TEncGOP.cpp',lambda s:s.replace('return NAL_UNIT_CODED_SLICE_IDR_W_RADL;','return NAL_UNIT_CODED_SLICE_IDR_N_LP;'))





# Compile the stock VS2015 solution with the installed VS2026 toolchain.
for p in (HM/'build').rglob('*.vcxproj'):
    s=(ORIGINAL/p.relative_to(HM)).read_text(encoding='utf-8').replace('v140','v145')
    s=s.replace('<WholeProgramOptimization>true</WholeProgramOptimization>','<WholeProgramOptimization>false</WholeProgramOptimization>')
    s=re.sub(r'<GenerateDebugInformation>.*?</GenerateDebugInformation>','<GenerateDebugInformation>false</GenerateDebugInformation>',s)
    s=re.sub(r'<DebugInformationFormat>.*?</DebugInformationFormat>','<DebugInformationFormat>None</DebugInformationFormat>',s)
    p.write_text(s,encoding='utf-8')

edit('source/Lib/TLibDecoder/TDecCu.cpp',lambda s:s.replace('#include "TDecCu.h"','#include "TDecCu.h"\n#include "TLibCommon/PocketStats.h"').replace('m_ppcCU[uiDepth]->copySubCU( pCtu, uiAbsPartIdx );','m_ppcCU[uiDepth]->copySubCU( pCtu, uiAbsPartIdx );\n  PocketStats::instance().leaf(m_ppcCU[uiDepth]);'))
edit('source/Lib/TLibDecoder/TDecGop.cpp',lambda s:s.replace('#include "TDecGop.h"','#include "TDecGop.h"\n#include "TLibCommon/PocketStats.h"').replace('  pcPic->compressMotion();','  PocketStats::instance().finish(pcPic);\n  pcPic->compressMotion();'))

(ROOT/'cfg').mkdir(exist_ok=True)
base=(HM/'cfg/encoder_lowdelay_P_main10.cfg').read_text(encoding='utf-8')
values={'Profile':'main','Level':'5','MaxCUWidth':'32','MaxCUHeight':'32','MaxPartitionDepth':'3','QuadtreeTULog2MaxSize':'4','QuadtreeTULog2MinSize':'2','QuadtreeTUMaxDepthIntra':'1','QuadtreeTUMaxDepthInter':'3','IntraPeriod':'30','DecodingRefreshType':'2','GOPSize':'1','IntraQPOffset':'0','LambdaFromQpEnable':'0','QP':'27','MaxCuDQPDepth':'1','MaxDeltaQP':'0','DeltaQpRD':'0','TransformSkip':'0','TransformSkipFast':'0','AMP':'0','InternalBitDepth':'8','LoopFilterOffsetInPPS':'1','LoopFilterDisable':'0','WaveFrontSynchro':'0','NumTileColumnsMinus1':'0','NumTileRowsMinus1':'0','SAO':'1','RateControl':'0'}
for key,value in values.items():
    pattern=r'^'+re.escape(key)+r'\s*:.*$'
    line=f'{key:<38}: {value}'
    if re.search(pattern,base,re.M):base=re.sub(pattern,line,base,flags=re.M)
    else:base+='\n'+line+'\n'
base=re.sub(r'^Frame\d+:.*\n?','',base,flags=re.M)
base+='\n# Low-delay I/P; each P picture references the immediately preceding picture.\n'
base+='\n'.join(f'Frame{i}: P {i} 0 0 0 0 0 1.0 0 0 0 1 1 -1 0' for i in range(1,2))+'\n'
base+='''
# Observed tools and deterministic fixed-QP test.
TMVPMode                              : 1
MaxNumMergeCand                       : 5
StrongIntraSmoothing                  : 0
SignHideFlag                          : 1
WeightedPredP                         : 0
WeightedPredB                         : 0
AdaptiveQP                            : 0
SEIDecodedPictureHash                  : 1
InputBitDepth                         : 8
OutputBitDepth                        : 8
InputChromaFormat                     : 420
FrameRate                             : 24
SourceWidth                           : 1920
SourceHeight                          : 1080
FramesToBeEncoded                     : 20
ConformanceWindowMode                 : 1
VuiParametersPresent                  : 1
PocProportionalToTimingFlag            : 1
'''
(ROOT/'cfg/pocket4_main8_qp27.cfg').write_text(base,encoding='utf-8')
optional=re.sub(r'^QuadtreeTUMaxDepthIntra\s*:.*$', 'QuadtreeTUMaxDepthIntra                 : 2',base,flags=re.M)
optional+='\n# Extension: CU8 intra RDO may choose one TU8 or four luma TU4.\n'
(ROOT/'cfg/pocket4_main8_intra8_tu4_qp27.cfg').write_text(optional,encoding='utf-8')


# Reviewable patch against the original code, including build compatibility.
patch=[]
for p in sorted(HM.rglob('*')):
    if p.is_file() and p.suffix in ('.cpp','.h','.vcxproj'):
        rel=p.relative_to(HM);q=ORIGINAL/rel
        before=q.read_text(encoding='utf-8').splitlines(True) if q.exists() else []
        after=p.read_text(encoding='utf-8').splitlines(True)
        if before!=after:patch.extend(difflib.unified_diff(before,after,fromfile='a/'+rel.as_posix(),tofile='b/'+rel.as_posix()))
(ROOT/'source_changes.patch').write_text(''.join(patch),encoding='utf-8')
print('Prepared source, config and source_changes.patch')
