// Local diagnostic extension. HM license remains in COPYING and source headers.
#ifndef POCKET_STATS_H
#define POCKET_STATS_H
#include "TComPic.h"
#include "TComDataCU.h"
#include <map>
#include <string>
#include <fstream>
#include <cstdlib>
#include <stdexcept>

// Counts final decoded leaves, never the encoder's temporary RD candidates.
// POCKET_STATS_FILE enables one compact JSON record per decoded picture.
class PocketStats {
  typedef std::map<int, unsigned long long> Counts;
  std::map<std::string, Counts> hist;
  unsigned long long skipped,merged,amvp,ts,cbfY;
  int maxMerge;
  std::ofstream out;
  bool active;
  PocketStats():skipped(0),merged(0),amvp(0),ts(0),cbfY(0),maxMerge(-1),active(false) {
    const char* path=std::getenv("POCKET_STATS_FILE");
    if(path && *path) {out.open(path);if(!out)throw std::runtime_error("Cannot open POCKET_STATS_FILE");active=true;}
  }
  UInt transforms(TComDataCU* cu,UInt index,UInt depth,UInt size,UInt count) {
    if(cu->getTransformIdx(index)>depth) {
      UInt leaves=0;
      for(UInt i=0;i<4;i++)leaves+=transforms(cu,index+i*count/4,depth+1,size/2,count/4);
      return leaves;
    }
    hist["luma_tu_size"][size]++;
    hist[cu->isIntra(0)?"intra_cu_tu_pairs":"inter_cu_tu_pairs"][cu->getWidth(0)*1024+size]++;
    hist["rqt_depth"][depth]++;
    hist[cu->isIntra(0)?"intra_luma_tu_size":"inter_luma_tu_size"][size]++;
    cbfY+=cu->getCbf(index,COMPONENT_Y,depth)!=0;
    if(cu->isIntra(0) && cu->getWidth(0)==16)hist["intra_cu16_luma_tu_size"][size]++;
    if(cu->isIntra(0) && cu->getWidth(0)==8) {
      hist["intra_cu8_luma_tu_size"][size]++;
      hist["intra_cu8_luma_tu_depth"][depth]++;
      if(cu->getCbf(index,COMPONENT_Y,depth))hist["intra_cu8_cbf_luma_tu_size"][size]++;
    }
    for(int c=0;c<3;c++) {
      // In 4:2:0, four luma TU4 share one chroma TU4 per component.
      // Do not invent 2x2 chroma TUs or count that shared TU four times.
      const UInt partsPer4=cu->getPic()->getNumPartitionsInCtu()*16/(cu->getSlice()->getSPS()->getMaxCUWidth()*cu->getSlice()->getSPS()->getMaxCUHeight());
      if(c>0 && size==4 && index%(4*partsPer4)!=0)continue;
      ts+=cu->getTransformSkip(index,ComponentID(c))!=0;
      hist[c==0?"luma_component_tu":"chroma_component_tu"][c==0?size:std::max<UInt>(4,size/2)]++;
    }
    return 1;
  }
public:
  static PocketStats& instance(){static PocketStats value;return value;}
  void leaf(TComDataCU* cu) {
    if(!active)return;
    const int size=cu->getWidth(0),part=cu->getPartitionSize(0);
    const bool intra=cu->isIntra(0);
    hist["cu_size"][size]++;hist["cu_depth"][cu->getDepth(0)]++;
    hist[intra?"intra_cu_size":"inter_cu_size"][size]++;
    hist["cu_qp"][cu->getQP(0)]++;
    // Track CUs intersecting the bottom 8 visible luma rows. This is a
    // regression probe for implicit boundary splits, not a mode constraint.
    const TComSPS* sps=cu->getSlice()->getSPS();
    const Window& crop=sps->getConformanceWindow();
    const int visibleBottom=sps->getPicHeightInLumaSamples()-crop.getWindowBottomOffset();
    if(int(cu->getCUPelY()) < visibleBottom && int(cu->getCUPelY())+size > visibleBottom-8) {
      hist["bottom_visible_cu_mode"][intra?1:0]++;
      hist["bottom_visible_cu_size"][size]++;
      hist[intra?"bottom_visible_intra_cu_size":"bottom_visible_inter_cu_size"][size]++;
      hist["bottom_visible_cu_partition"][part]++;
    }

    hist["cu_partition"][part]++;
    skipped+=cu->isSkipped(0);
    const int n=part==SIZE_2Nx2N?1:part==SIZE_NxN?4:2;
    for(int p=0;p<n;p++) {
      UInt addr=0;Int w=0,h=0;cu->getPartIndexAndSize(p,addr,w,h);
      hist["pu_partition"][part]++;
      hist[intra?"intra_pu_dimensions":"inter_pu_dimensions"][w*1024+h]++;
      if(!intra && w==8 && h==8)hist["inter_pu8x8_cu_size"][size]++;
      if(intra) {
        hist["intra_pu_width"][w]++;
        hist["intra_luma_mode"][cu->getIntraDir(CHANNEL_TYPE_LUMA,addr)]++;
        hist["intra_chroma_mode"][cu->getIntraDir(CHANNEL_TYPE_CHROMA,addr)]++;
      } else {
        const bool merge=cu->getMergeFlag(addr);
        merged+=merge;amvp+=!merge;
        if(merge) {hist["merge_index"][cu->getMergeIndex(addr)]++;maxMerge=std::max(maxMerge,int(cu->getMergeIndex(addr)));}
        for(int l=0;l<2;l++)if(!std::getenv("CAMERA_STATS_FAST") && cu->getCUMvField(RefPicList(l))->getRefIdx(addr)>=0) {
          TComMv mv=cu->getCUMvField(RefPicList(l))->getMv(addr);
          hist["mv_x_quarterpel"][mv.getHor()]++;hist["mv_y_quarterpel"][mv.getVer()]++;
        }
      }
    }
    if(intra || cu->getQtRootCbf(0)) {
      const UInt leaves=transforms(cu,0,0,size,cu->getPic()->getNumPartitionsInCtu()>>(2*cu->getDepth(0)));
      hist[intra?"intra_cu_tu_leaf_counts":"inter_cu_tu_leaf_counts"][size*1024+leaves]++;
      if(intra && size==8) {
        hist["intra_cu8_luma_tu_leaves_per_cu"][leaves]++;
        hist["intra_cu8_pu_partition"][part]++;
      }
    }
  }
  void finish(TComPic* pic) {
    if(!active)return;
    TComSlice* sl=pic->getSlice(0);const TComSPS* sp=sl->getSPS();const TComPPS* pp=sl->getPPS();
    out<<"{\"poc\":"<<sl->getPOC()<<",\"type\":\""<<(sl->isIntra()?"I":sl->isInterP()?"P":"B")<<"\",\"slice_qp\":"<<sl->getSliceQp();
    const Window& crop=sp->getConformanceWindow();
    out<<",\"coded_width\":"<<sp->getPicWidthInLumaSamples()<<",\"coded_height\":"<<sp->getPicHeightInLumaSamples();
    out<<",\"crop_left\":"<<crop.getWindowLeftOffset()<<",\"crop_right\":"<<crop.getWindowRightOffset()<<",\"crop_top\":"<<crop.getWindowTopOffset()<<",\"crop_bottom\":"<<crop.getWindowBottomOffset();
    out<<",\"bitdepth\":"<<sp->getBitDepth(CHANNEL_TYPE_LUMA)<<",\"ctu_size\":"<<sp->getMaxCUWidth();
    out<<",\"min_cu\":"<<(1<<sp->getLog2MinCodingBlockSize())<<",\"max_cu\":"<<(1<<(sp->getLog2MinCodingBlockSize()+sp->getLog2DiffMaxMinCodingBlockSize()));
    out<<",\"min_tu\":"<<(1<<sp->getQuadtreeTULog2MinSize())<<",\"max_tu\":"<<(1<<sp->getQuadtreeTULog2MaxSize());
    out<<",\"syntax_intra_transform_depth\":"<<sp->getQuadtreeTUMaxDepthIntra()-1<<",\"syntax_inter_transform_depth\":"<<sp->getQuadtreeTUMaxDepthInter()-1;
    out<<",\"amp\":"<<sp->getUseAMP()<<",\"tmvp_sps\":"<<sp->getSPSTemporalMVPEnabledFlag()<<",\"tmvp_slice\":"<<sl->getEnableTMVPFlag();
    out<<",\"ts_allowed\":"<<pp->getUseTransformSkip()<<",\"sao\":"<<sp->getUseSAO()<<",\"strong_intra_smoothing\":"<<sp->getUseStrongIntraSmoothing();
    out<<",\"pcm\":"<<sp->getUsePCM()<<",\"tiles\":"<<pp->getTilesEnabledFlag()<<",\"wpp\":"<<pp->getEntropyCodingSyncEnabledFlag();
    out<<",\"deblocking_control_present\":"<<pp->getDeblockingFilterControlPresentFlag()<<",\"deblocking_disabled\":"<<sl->getDeblockingFilterDisable();
    out<<",\"sign_hiding\":"<<pp->getSignDataHidingEnabledFlag()<<",\"weighted_pred_p\":"<<pp->getUseWP()<<",\"weighted_pred_b\":"<<pp->getWPBiPred();
    out<<",\"scaling_list\":"<<sp->getScalingListFlag()<<",\"constrained_intra\":"<<pp->getConstrainedIntraPred();
    out<<",\"transquant_bypass_allowed\":"<<pp->getTransquantBypassEnabledFlag()<<",\"cabac_init_present\":"<<pp->getCabacInitPresentFlag();
    out<<",\"tile_cols\":"<<pp->getNumTileColumnsMinus1()+1<<",\"tile_rows\":"<<pp->getNumTileRowsMinus1()+1;
    out<<",\"tile_uniform\":"<<pp->getTileUniformSpacingFlag()<<",\"nal_type\":"<<int(sl->getNalUnitType())<<",\"temporal_id\":"<<sl->getTLayer();
    out<<",\"beta_offset\":"<<sl->getDeblockingFilterBetaOffsetDiv2()<<",\"tc_offset\":"<<sl->getDeblockingFilterTcOffsetDiv2();
    out<<",\"ref_pocs\":[";
    for(int l=0;l<2;l++){if(l)out<<",";out<<"[";for(int i=0;i<sl->getNumRefIdx(RefPicList(l));i++){if(i)out<<",";out<<sl->getRefPOC(RefPicList(l),i);}out<<"]";}out<<"]";
    out<<",\"dqp_enabled\":"<<pp->getUseDQP()<<",\"qg_size\":"<<(sp->getMaxCUWidth()>>pp->getMaxCuDQPDepth());
    out<<",\"max_merge_candidates\":"<<sl->getMaxNumMergeCand()<<",\"l0_refs\":"<<sl->getNumRefIdx(REF_PIC_LIST_0)<<",\"l1_refs\":"<<sl->getNumRefIdx(REF_PIC_LIST_1);
    out<<",\"skip_cus\":"<<skipped<<",\"merge_pus\":"<<merged<<",\"amvp_pus\":"<<amvp<<",\"transform_skip_tus\":"<<ts<<",\"luma_cbf_tus\":"<<cbfY<<",\"max_merge_index\":"<<maxMerge;
    out<<",\"histograms\":{";bool first=true;
    for(std::map<std::string,Counts>::const_iterator h=hist.begin();h!=hist.end();++h) {
      if(!first)out<<",";first=false;out<<"\""<<h->first<<"\":{";bool f=true;
      for(Counts::const_iterator c=h->second.begin();c!=h->second.end();++c){if(!f)out<<",";f=false;out<<"\""<<c->first<<"\":"<<c->second;}out<<"}";
    }
    out<<"}}\n";out.flush();if(!out)throw std::runtime_error("Pocket stats write failed");
    hist.clear();skipped=merged=amvp=ts=cbfY=0;maxMerge=-1;
  }
};
#endif
