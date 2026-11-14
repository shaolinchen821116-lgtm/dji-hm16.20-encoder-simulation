# Action6 HM 16.20 仿真报告

日期：2026-11-15。

## 原片分析

- 文件：`dji_mimo_20251129_110920_0_1764536541683_video.mp4`。
- 完整解码 **716 帧**，类型：`{'I': 24, 'P': 692}`。
- 原片为 Main10、3840×2160；实际播放帧率 30000/1001，I 间隔 30 帧。
- 原片 Tiles：4 列 × 1 行。
- 参数集、逐块观察和置信边界分别保留；完整统计见 source_analysis/analysis.json，工具表见 source_analysis/tools_full_clip.csv。

| 原片工具/结构 | 信令值或实际观察值 |
| --- | --- |
| CTU size | 32 |
| Maximum TU size | 32 |
| Intra transform hierarchy | 0 |
| Inter transform hierarchy | 0 |
| AMP | 0 |
| TMVP | 1 |
| Sign data hiding | 0 |
| CABAC init present | 1 |
| QG size | 32 |
| P merge candidate limit | 3 |
| Deblocking beta offset /2 | 0 |
| Deblocking tc offset /2 | 0 |
| Intra CU sizes | 8,16,32 |
| Inter CU sizes | 8,16,32 |
| Intra PU widths | 8,16,32 |
| Inter luma TU sizes | 8,16,32 |

变换层级为标准语法值，对应 HM 配置值需加 1。SPS 最小 TU4 不代表每类 CU 都允许或实际使用 TU4；TU 和 PU 不能混为一谈。

## 仿真设置和有意差异

- 输入 ParkScene_1920x1080_24.yuv 前 20 帧，8 bit YUV420；内部编码也为 8 bit，Profile=Main，QP 恒为 27。
- 显示 1920×1080、24 fps，1 I + 19 P，单活动 L0 参考，无 B 帧。
- **按用户要求，仿真 Tiles 全部关闭，1×1；原片的 4 列 Tiles 仅在原片表中保留，不用于仿真。**
- 其他工具配置和候选结构按照原片信令及完整样本的观察集合实现。固定 QP 不复现原片 AQ、码控或模式使用比例。
- Action6 原片编码高度2176、显示2160；其本次编码高度1088、显示1080，采用相同的向下补齐并裁剪原则。其余三个测试保持编码高度1080。

## 验证结果

- 20 帧测试全部通过；码流 **566,305 字节**，含头信息码率 **5436.528 kbit/s**。
- 平均逐帧 PSNR：Y 37.5127 dB，U 39.7888 dB，V 41.0312 dB。
- 20 个 decoded picture hash SEI 的 MD5 全部 OK；编码器重建、HM 解码、FFmpeg 独立解码逐字节一致。
- 另用 65 帧 64×64 小序列验证完整 I 周期：I 解码序号 `[0, 30, 60]`，NAL 类型 `19`；65 帧 MD5 全部 OK，所有 P slice 均为单参考，Tiles 关闭。
- 结果位于 output/verification.json、output/gop_probe/verification.json；编码日志、解码日志、参数集跟踪、逐帧 PSNR 表均保留。

## 代码与复现

CameraPolicy.h 给出独立的相机策略；TEncCu.cpp 限制最终候选 CU/PU；TEncSearch.cpp 实现 Intra/TU 对应和 Inter TU 范围；TEncTop.cpp 对齐 DQP、CABAC init 和 VUI；TEncGOP.cpp 对齐 IDR 类型。解码器另有可关闭统计钩子。

代码由未修改的 HM-HM-16.20 独立复制，未从其他相机的定制目录复制。完整差异见 source_changes.patch。

配置：`cfg/camera_main8_qp27.cfg`。双击 build.bat 编译。使用 Python 3.10+、FFmpeg、Visual Studio 2026 Community/v145；其他 VS 版本需调整构建脚本和工具集。输入序列在脚本中配置，数据文件不包含在源码包中。

```powershell
python run_test.py
python run_test.py --verify-only
python gop_probe.py
```

source_changes.patch 用于审阅相对原版的修改。已提供完整修改后源码，正常编译不需要运行生成源码用的 prepare.py。HM 原始版权和许可保留在 HM-16.20/COPYING。

“未观察到”不能直接解释为硬件“不支持”。这里复现的是可审阅的 HM 工具配置与搜索限制，不能声称复制了 DJI 的私有算法、码控或压缩效率。
