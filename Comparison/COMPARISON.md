# DJI 四机型 HEVC 工具比较

2026-11-15。全部四份源片完整解码：Action6 716 帧、Air3S 1875 帧、Mavic3 480 帧、Pocket4 328 帧，共 **3,399 帧**。

## 主要发现

- 四份源片均为 Main10、4:2:0、4K、单参考低延迟 I/P。前三份实际播放帧率为 30000/1001，Pocket4 为 60000/1001。Air3S 文件名的“120fps”不等于文件实际播放帧率。
- Action6：CTU32、TU 最大32、无可选 Intra RQT；Inter 的矩形 PU 可能产生规范强制 TU 下分，即使 SPS Inter 变换层级语法值为0。原片四列 Tiles，P Merge 上限3，CABAC init present=1，符号隐藏关闭。
- Air3S：CTU32、TU 最大16、Intra8/16、Inter8/16/32、TMVP 和符号隐藏开启。原片两列 Tiles，QG32，I周期60。
- Mavic3：CTU64但实际叶 CU 最大32，AMP 开启、TMVP 关闭，大量 Intra4 PU 和亮度 TU4；β偏移/2=5、tc偏移/2=-2，P Merge 上限3，符号隐藏关闭。
- Pocket4：CTU32、TU 最大16、Intra8/16、Inter8/16；全片真正 Inter CU8 仅6个。原片没有观察到 Intra CU8/单 PU8 再分四 TU4，默认模仿配置保持单 TU8，可选四 TU4 扩展另行保留。

## 相似度

定义为 Excel 中明确列出的 **34 个原片工具配置及结构字段的等权精确匹配率**。排除位深、分辨率、帧率、码率、QP 分布和模式频率。Excel 保留逐字段匹配与可重算公式，CSV 可独立核对。

| 两机型 | 匹配字段 | 配置匹配率 |
| --- | ---: | ---: |
| Action6 / Air3S | 22/34 | 64.7% |
| Action6 / Mavic3 | 21/34 | 61.8% |
| Action6 / Pocket4 | 21/34 | 61.8% |
| Air3S / Mavic3 | 15/34 | 44.1% |
| Air3S / Pocket4 | 30/34 | 88.2% |
| Mavic3 / Pocket4 | 17/34 | 50.0% |

Air3S 与 Pocket4 最接近，主要四项差异为 I 周期、Tiles 列数、QG 大小和是否观察到 Inter CU32。Mavic3 与这一组差异较大，体现在 CTU64、AMP、TMVP、Intra4 和更深的变换树。这个比例描述工具配置，不代表芯片相同、私有编码算法相同或画质相似度。

## 统一仿真和验证

全部默认配置使用 ParkScene 前20帧、8bit/Main、1920×1080、24fps、QP27、单参考。**根据用户最新要求，四套仿真均关闭 Tiles**；原片 Action6/Air3S 的 Tiles 仍作为原片事实参与上表。

| 工程 | 码流字节 | 含头信息 kbit/s | 平均 Y-PSNR dB | 重建验证 |
| --- | ---: | ---: | ---: | --- |
| Action6 | 566,305 | 5436.528 | 37.5127 | 通过 |
| Air3S | 552,348 | 5302.541 | 37.4960 | 通过 |
| Mavic3 | 558,633 | 5362.877 | 37.6633 | 通过 |
| Pocket4 | 559,920 | 5375.232 | 37.4890 | 通过 |

四套共80帧均通过 MD5 与编码器/HM/FFmpeg 三方逐字节重建比较。另有四套各65帧小序列，共260帧，实际验证 I周期30/60、IDR类型、单参考和关闭Tiles；MD5全部通过。Pocket4可选四TU4另有20帧验证，不作为默认四机型对比的第五组。

固定QP结果不构成完整率失真比较，不能据一组QP排名编码器效率。AQ/码控、MV搜索策略和模式占比不能仅凭码流唯一反推，相关边界在工程报告中说明。

## 文件

- Excel：outputs/dji-four-cameras-20261115/DJI_four_camera_tools.xlsx，含工具表、可重算相似度、源文件证据。
- 合并 CSV：DJI_tools_comparison.csv；相似度CSV：DJI_similarity.csv。
- 各机型完整工具表：Action6/tools.csv、Air3S/tools.csv、Mavic3/tools.csv、Pocket4/tools.csv。
- 全片逐帧统计在本地各机型目录 tools_all_frames.jsonl；源码压缩包保留概要统计和工具CSV，不包含原视频轨或重建YUV。

## 工程交付

四个指定目录各自包含完整 HM 源码、独立配置、构建和验证脚本、源码差异与报告。GitHub源码包保留HM原版权许可，排除原始视频、原始YUV、逐像素重建、中间编译文件和本机虚拟环境。所有压缩包附清单与SHA256，并进行CRC和逐文件哈希验证。
