# Pocket 4 HM 修正与验证结果

## 完成的修正

1. **开放 Inter CU8**。全片分析确认原片存在 6 个真正的 Inter CU8；上一版只根据前 10 帧 CSV 禁用它，造成 1080 高度的底部边界 CU8 在 P 帧也只能选 Intra。现允许 CU8 的 8×8 PU 进行 Merge/Skip/AMVP 搜索，保留 CU16 和两种矩形 PU。
2. **保留原生 1920×1080 编码尺寸**。HM 的正常边界划分得到 CU8 后，恢复 Inter 与 Intra 的 RD 竞争；最终方案不依赖编码高度补齐到 1088，也不强制边界块一定选 Inter。
3. **新增可选 Intra8/四 TU4**。原片全部 297,682 个 Intra CU8 都是单 TU8，所以默认模仿配置仍保持 TU8；另提供扩展配置让 Intra8 在 TU8 与四 TU4 之间选择。两套均为 8 bit/QP27/20 帧。

源片的全片核对与定位见 [DJI_FINDINGS.md](source_analysis/DJI_FINDINGS.md)。原始 HM 目录和输入 YUV 未改动；旧码流保存在 output/border_fix/before_fix.265。

## 支持配置

| 项目 | 最终设置 |
| --- | --- |
| 输入和输出 | ParkScene 前 20 帧；8 bit、Main、YUV420、24 fps；QP=27 |
| 编码/显示尺寸 | 均为 1920×1080，不补成 1088；底部保留正常的边界 CU8 |
| CTU / 叶 CU | CTU32；叶 CU8/16；CU32 强制拆分 |
| Intra PU | CU8/16 的单个 2N×2N PU，无 4×4 Intra PU |
| Inter PU | CU8：仅 8×8；CU16：16×16、16×8、8×16 |
| Inter 工具 | CU8/16 均可搜索 Skip、Merge、AMVP；TMVP 开启；Merge 上限 5 |
| 默认亮度变换 | Intra8/TU8、Intra16/TU16；Inter TU8/16，无 Inter TU4 |
| 可选亮度变换 | Intra8 可选单 TU8 或四 TU4，通过 RD 选择；Intra16 保持 TU16 |
| TU 层级 | 默认 Intra HM 配置 1（SPS 语法 0）；可选配置 2（SPS 语法 1）；Inter 配置 3（语法 2） |
| 色度 Intra | DM（36）；色度 TU4 按 4:2:0 的共享规则处理，不是 2×2 TU |
| 关闭工具 | AMP、NxN PU、Intra4、TS、PCM、强 Intra smoothing、加权预测、Tiles、WPP |
| 保留工具 | SAO、Deblocking、符号隐藏；QG16 和 QP delta 信令，本测试所有 CU QP 恒为 27 |
| 参考 / GOP | 单活动 L0、无 L1，1 I + 19 P；配置 I 周期 30，本轮未覆盖完整周期 |

## 底部最后 8 行专项验证

区域：x=0～1919、y=1072～1079，19 个 P 帧。

| 项目 | 修正前 | 最终修正后 |
| --- | ---: | ---: |
| Intra CU 数 | 4,560 | 17 |
| Inter CU 数 | 0 | 4,543 |
| Inter 可见面积占比 | 0.0000% | 99.6272% |

每个 P 帧底部都有 Inter 块。残留 Intra 是正常 RD 选择，程序没有强制全部 Inter。编码高度和显示高度均确认 1080，crop_bottom=0。详细逐帧表见 output/border_fix/bottom_row_comparison.csv；机器可读结果见 border_verification.json。

## 20 帧测试结果

输入：`D:/yuv_data/yuv_hevc/ClassB/ParkScene_1920x1080_24.yuv`，帧 0～19。

| 项目 | 默认模仿配置 | 可选 Intra8/四 TU4 |
| --- | ---: | ---: |
| 帧数 / QP | 20 / 27 | 20 / 27 |
| I / P | 1 / 19 | 1 / 19 |
| 码流字节 | 559,920 | 559,570 |
| 含头信息码率 kbit/s | 5375.232 | 5371.872 |
| 平均 Y-PSNR dB | 37.4890 | 37.5052 |
| 实际 Inter CU8 | 106,201 | 109,680 |
| Intra CU8 选择四 TU4 的数量 | 0 | 3,796 |
| Intra CU8 下非零 CBF 的亮度 TU4 数量 | 0 | 11,398 |
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
