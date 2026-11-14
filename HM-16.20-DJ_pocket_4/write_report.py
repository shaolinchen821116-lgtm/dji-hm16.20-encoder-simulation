"""Generate current delivery reports from verified native-size experiments."""
from pathlib import Path
import json,csv,hashlib
ROOT=Path(__file__).resolve().parent
r=json.loads((ROOT/'output/verification.json').read_text(encoding='utf-8'))
e=json.loads((ROOT/'output/intra8_tu4/verification.json').read_text(encoding='utf-8'))
b=json.loads((ROOT/'output/border_fix/border_verification.json').read_text(encoding='utf-8'))
s=json.loads((ROOT/'source_analysis/source_findings.json').read_text(encoding='utf-8'))
assert r['passed'] and e['passed'] and b['passed']
assert r['headers_checked']['coded_height']==1080 and r['headers_checked']['crop_bottom']==0
assert not r['intra8_tu4_extension'] and e['intra8_tu4_extension']
assert s['pictures_decoded']==328 and s['actual_inter_cu8_count']>0
assert hashlib.sha256((ROOT/'bin/TAppEncoder_pocket4.exe').read_bytes()).hexdigest()==r['encoder_sha256']==e['encoder_sha256']
source_frames=[json.loads(line) for line in (ROOT/'source_analysis/tools_all_frames.jsonl').read_text().splitlines()]
rare=[{'decode_index':i,'poc':f['poc'],'type':f['type'],'inter_cu8_count':f['histograms'].get('inter_cu_size',{}).get('8',0)} for i,f in enumerate(source_frames) if f['histograms'].get('inter_cu_size',{}).get('8',0)]
s['inter_cu8_observations']=rare
(ROOT/'source_analysis/source_findings.json').write_text(json.dumps(s,indent=2),encoding='utf-8')
rows='\n'.join(f"| {v['decode_index']} | {v['poc']} | {v['type']} | {v['inter_cu8_count']} |" for v in rare)
findings=f"""# DJI 原始码流全片核对

源文件：`C:/Users/shaol/Downloads/DJI_20260429163710_0019_D.MP4`。

完整提取视频轨，不重编码，使用 HM 逐块解码全部 **{s['pictures_decoded']} 帧**。原片为 Main10、3840×2160、60000/1001 fps，包含 {s['frame_types']['I']} 个 I 帧、{s['frame_types']['P']} 个 P 帧。这里只分析现有码流；新增编码实验均为用户要求的 8 bit。

## Inter8 的结论

**原码流实际使用了 Inter CU8，但并非只使用或只支持 Inter8。**

| 结构 | 实际数量 |
| --- | ---: |
| Inter CU16（含 Skip） | {s['inter_cu_sizes'].get('16',0):,} |
| Inter CU8（含 Skip） | {s['actual_inter_cu8_count']:,} |
| 16×16 Inter PU | {s['inter_pu_dimensions'].get('16x16',0):,} |
| 16×8 Inter PU | {s['inter_pu_dimensions'].get('16x8',0):,} |
| 8×16 Inter PU | {s['inter_pu_dimensions'].get('8x16',0):,} |
| 8×8 Inter PU，所属 CU8 | {s['actual_inter_pu8x8_count']:,} |

六个 8×8 PU 都属于真正的 CU8，并非把 CU16 内的矩形 PU 宽度误称为 Inter8。CSV 只分析前 10 帧，遗漏了这些极少见的结构；据此前 10 帧就禁用 Inter8 是上一版代码的错误限制。

| 解码序号（从 0 开始） | POC | 类型 | Inter CU8 数量 |
| ---: | ---: | --- | ---: |
{rows}

POC 在随机接入周期中重置，因此定位时同时使用全局解码序号和 POC。计数来自最终解码叶 CU 和实际 PU 几何，不是编码器临时候选。原片使用 Inter8 是已观察事实；硬件完整支持集不能仅由某个模式未出现推断。

## Intra8 / 四个亮度 TU4 的结论

原片的 **{s['intra_cu8_count']:,} 个 Intra CU8 均为一个 8×8 PU、一个亮度 TU8**，没有观察到 Intra CU8 下的 TU4。具有非零亮度 CBF 的 CU8/TU8 有 {s['intra_cu8_nonzero_luma_tu_sizes'].get('8',0):,} 个。

所有实际 SPS 的 `max_transform_hierarchy_depth_intra` 语法值为 0；在这里的 CU8 / 2N×2N Intra 结构下不允许继续下分为四个 TU4。`log2_min_luma_transform_block_size_minus2=0` 只说明总体最小 TU 为 4，不能证明 Intra CU8 可以下分。也不能把色度 TU4 当成亮度 TU4。

因此，**这份原码流未使用、也未在其现有 CU8/单 PU8 结构中开放四 TU4**；这不等同于证明 DJI 硬件没有其他编码配置可以支持。为用户新增需求，当前 HM 另提供可选四 TU4 配置，默认模仿配置仍保持 Intra8/TU8。

## 可重复证据

- `source_findings.json`：完整统计与原片 SHA256。
- `tools_all_frames.jsonl`：逐帧 CU/PU/TU 结构统计。
- `cu8_tu_and_inter_per_picture.csv`：逐帧 CU8 / TU4 核对表。
- `headers_trace.log`：FFmpeg 独立参数集语法跟踪。
- `decoder.log`：328 帧 HM 解码日志。

重新分析：`python analyze_dji.py`。提取的 `dji_source.265` 是原视频轨的 Annex B 表示，没有重新编码。
"""
(ROOT/'source_analysis/DJI_FINDINGS.md').write_text(findings,encoding='utf-8')

h=r['histograms'];eh=e['histograms']
settings='\n'.join(f"| {title} | {value} |" for title,value in [
('输入和输出','ParkScene 前 20 帧；8 bit、Main、YUV420、24 fps；QP=27'),
('编码/显示尺寸','均为 1920×1080，不补成 1088；底部保留正常的边界 CU8'),
('CTU / 叶 CU','CTU32；叶 CU8/16；CU32 强制拆分'),
('Intra PU','CU8/16 的单个 2N×2N PU，无 4×4 Intra PU'),
('Inter PU','CU8：仅 8×8；CU16：16×16、16×8、8×16'),
('Inter 工具','CU8/16 均可搜索 Skip、Merge、AMVP；TMVP 开启；Merge 上限 5'),
('默认亮度变换','Intra8/TU8、Intra16/TU16；Inter TU8/16，无 Inter TU4'),
('可选亮度变换','Intra8 可选单 TU8 或四 TU4，通过 RD 选择；Intra16 保持 TU16'),
('TU 层级','默认 Intra HM 配置 1（SPS 语法 0）；可选配置 2（SPS 语法 1）；Inter 配置 3（语法 2）'),
('色度 Intra','DM（36）；色度 TU4 按 4:2:0 的共享规则处理，不是 2×2 TU'),
('关闭工具','AMP、NxN PU、Intra4、TS、PCM、强 Intra smoothing、加权预测、Tiles、WPP'),
('保留工具','SAO、Deblocking、符号隐藏；QG16 和 QP delta 信令，本测试所有 CU QP 恒为 27'),
('参考 / GOP','单活动 L0、无 L1，1 I + 19 P；配置 I 周期 30，本轮未覆盖完整周期')])
report=f"""# Pocket 4 HM 修正与验证结果

## 完成的修正

1. **开放 Inter CU8**。全片分析确认原片存在 6 个真正的 Inter CU8；上一版只根据前 10 帧 CSV 禁用它，造成 1080 高度的底部边界 CU8 在 P 帧也只能选 Intra。现允许 CU8 的 8×8 PU 进行 Merge/Skip/AMVP 搜索，保留 CU16 和两种矩形 PU。
2. **保留原生 1920×1080 编码尺寸**。HM 的正常边界划分得到 CU8 后，恢复 Inter 与 Intra 的 RD 竞争；最终方案不依赖编码高度补齐到 1088，也不强制边界块一定选 Inter。
3. **新增可选 Intra8/四 TU4**。原片全部 297,682 个 Intra CU8 都是单 TU8，所以默认模仿配置仍保持 TU8；另提供扩展配置让 Intra8 在 TU8 与四 TU4 之间选择。两套均为 8 bit/QP27/20 帧。

源片的全片核对与定位见 [DJI_FINDINGS.md](source_analysis/DJI_FINDINGS.md)。原始 HM 目录和输入 YUV 未改动；旧码流保存在 output/border_fix/before_fix.265。

## 支持配置

| 项目 | 最终设置 |
| --- | --- |
{settings}

## 底部最后 8 行专项验证

区域：x=0～1919、y=1072～1079，19 个 P 帧。

| 项目 | 修正前 | 最终修正后 |
| --- | ---: | ---: |
| Intra CU 数 | {b['before']['intra_cus']:,} | {b['after']['intra_cus']:,} |
| Inter CU 数 | {b['before']['inter_cus']:,} | {b['after']['inter_cus']:,} |
| Inter 可见面积占比 | {b['before']['inter_visible_area_percent']:.4f}% | {b['after']['inter_visible_area_percent']:.4f}% |

每个 P 帧底部都有 Inter 块。残留 Intra 是正常 RD 选择，程序没有强制全部 Inter。编码高度和显示高度均确认 1080，crop_bottom=0。详细逐帧表见 output/border_fix/bottom_row_comparison.csv；机器可读结果见 border_verification.json。

## 20 帧测试结果

输入：`D:/yuv_data/yuv_hevc/ClassB/ParkScene_1920x1080_24.yuv`，帧 0～19。

| 项目 | 默认模仿配置 | 可选 Intra8/四 TU4 |
| --- | ---: | ---: |
| 帧数 / QP | 20 / 27 | 20 / 27 |
| I / P | 1 / 19 | 1 / 19 |
| 码流字节 | {r['bitstream_bytes']:,} | {e['bitstream_bytes']:,} |
| 含头信息码率 kbit/s | {r['bitrate_kbps_including_headers']:.3f} | {e['bitrate_kbps_including_headers']:.3f} |
| 平均 Y-PSNR dB | {r['mean_picture_psnr_db']['Y']:.4f} | {e['mean_picture_psnr_db']['Y']:.4f} |
| 实际 Inter CU8 | {h['inter_cu_size'].get('8',0):,} | {eh['inter_cu_size'].get('8',0):,} |
| Intra CU8 选择四 TU4 的数量 | {h.get('intra_cu8_luma_tu_leaves_per_cu',{}).get('4',0):,} | {eh.get('intra_cu8_luma_tu_leaves_per_cu',{}).get('4',0):,} |
| Intra CU8 下非零 CBF 的亮度 TU4 数量 | {h.get('intra_cu8_cbf_luma_tu_size',{}).get('4',0):,} | {eh.get('intra_cu8_cbf_luma_tu_size',{}).get('4',0):,} |
| HM MD5 通过帧数 | 20 | 20 |
| 编码器 / HM / FFmpeg 重建逐字节一致 | 是 | 是 |

PSNR 为逐帧值的算术平均。两套解码输出均为 20 帧 1920×1080 YUV420 8 bit，各 62,208,000 字节。默认与扩展输出之间不要求相同；各自须与自身编码器重建一致。

扩展配置还逐帧验证：每个 Intra CU8 只有 1 或 4 个亮度 TU；TU4 总数等于四 TU4 CU 数的 4 倍；Intra16 仍为 TU16；Inter 不使用 TU4；没有把四 TU4 误当成四个 Intra4 PU；TS 始终关闭。

## 交付路径与复现

- 源码：HM-16.20；完整差异：source_changes.patch。
- 默认配置：cfg/pocket4_main8_qp27.cfg。
- 可选配置：cfg/pocket4_main8_intra8_tu4_qp27.cfg。
- 默认码流：output/ParkScene_1920x1080_24_pocket4_qp27_20f.265。
- 可选码流：output/intra8_tu4/ParkScene_1920x1080_24_pocket4_qp27_20f.265。
- 两套目录均保留 encoder.log、decoder.log、verification.json、decoded_tools.jsonl、picture_results.csv、supported_configuration.csv 和独立解码重建文件。

```powershell
python run_encode.py
python verify.py
python check_border.py
python run_encode.py --intra8-tu4
python verify.py --intra8-tu4
```

`python test_extensions.py` 会并行编码两个独立输出，再逐个验证。`build.bat` 使用本机 Visual Studio 2026 Community/v145，verify.py 使用 C:/ffmpeg/bin 的 FFmpeg 和 ffprobe。编译后的两个程序位于 bin。

## 修改位置

- TEncCu.cpp：开放 CU8 Inter 的 8×8 PU、Merge/Skip 与 AMVP；限制 CU16 对称矩形 PU；保留 Intra8/16 和有效候选保护。
- TEncSearch.cpp：只允许可选的 Intra CU8 下分 TU4；Intra16 不下分；Inter 禁用 TU4；色度 Intra 仅 DM。
- TEncTop.cpp：无 HRD 时也写入配置帧率的 VUI 时序。
- PocketStats.h / TDecCu.cpp / TDecGop.cpp：统计实际 CU/PU 几何、CU8 与 TU 对应关系、最后 8 行模式与编码/显示尺寸。TU4 色度共享计数正确。
- prepare.py 和验证脚本：保留可重复差异、默认/扩展配置及原片全片分析。

全片观察不能等同于硬件完整能力表。当前模式约束基于该文件实际结构和用户明确要求；未模仿原片的 AQ 算法、QP 分布、MV 分布或模式比例。
"""
(ROOT/'RESULTS.md').write_text(report,encoding='utf-8')
(ROOT/'README.md').write_text("""# HM 16.20 Pocket 4 experiment

独立 HM 编码器，8 bit / Main、ParkScene 1920×1080 24 fps、20 帧、QP=27。

已修复底部强制 Intra：开放 Inter CU8，保留原生编码高度 1080。另提供可选 Intra8/四个亮度 TU4。

- [最终结果与支持配置](RESULTS.md)
- [DJI 原片全部 328 帧的分析结论](source_analysis/DJI_FINDINGS.md)
- [默认码流](output/ParkScene_1920x1080_24_pocket4_qp27_20f.265)
- [可选四 TU4 码流](output/intra8_tu4/ParkScene_1920x1080_24_pocket4_qp27_20f.265)
- [默认配置](cfg/pocket4_main8_qp27.cfg)
- [可选配置](cfg/pocket4_main8_intra8_tu4_qp27.cfg)

build.bat 编译；test_parkscene.bat 测默认配置；python test_extensions.py 测两套配置。命令和边界说明见 RESULTS.md。HM 原始许可位于 HM-16.20/COPYING。
""",encoding='utf-8')
print('Written current RESULTS.md, README.md and source_analysis/DJI_FINDINGS.md')
