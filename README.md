# DJI HM 16.20 编码配置实验

包含 Action6、Air3S、Mavic3、Pocket 4 四套独立 HM 16.20 源码，以及完整原片分析、工具配置比较、相似度和测试结果。

## 四套代码

| 机型 | 工程目录 | CTU | 最大 TU | 原片 Tiles | 仿真 Tiles |
| --- | --- | ---: | ---: | --- | --- |
| Action6 | [HM_16.20_DJ_Action6](HM_16.20_DJ_Action6) | 32 | 32 | 4列 | 关闭 |
| Air3S | [HM-16.20-DJ_Air3S](HM-16.20-DJ_Air3S) | 32 | 16 | 2列 | 关闭 |
| Mavic3 | [HM_16.20_DJ_Mavic3](HM_16.20_DJ_Mavic3) | 64 | 32 | 关闭 | 关闭 |
| Pocket 4 | [HM-16.20-DJ_pocket_4](HM-16.20-DJ_pocket_4) | 32 | 16 | 关闭 | 关闭 |

原片共完整分析 3,399 帧。统一仿真采用 ParkScene、8 bit/Main、1920×1080、24 fps、QP=27、20帧、关闭 Tiles。四套均通过 HM/FFmpeg 与编码器重建的逐字节比较。另用四套各65帧小序列验证完整 I 周期、单参考和 IDR 类型。

## 工具对比与相似度

- [详细比较与实验总结](Comparison/COMPARISON.md)
- [Excel 工具表、可重算相似度和来源](Comparison/outputs/dji-four-cameras-20261115/DJI_four_camera_tools.xlsx)
- [工具对比 CSV](Comparison/DJI_tools_comparison.csv)
- [相似度 CSV](Comparison/DJI_similarity.csv)

相似度定义为列明的34个原片工具配置及结构字段的等权精确匹配率。Air3S 与 Pocket 4 最接近，为88.2%。这不代表画质、芯片或私有编码算法相同。

## 全部原始码流和配套文件

[Release v2026.11.15](https://github.com/shaolinchen821116-lgtm/dji-hm16.20-encoder-simulation/releases/tag/v2026.11.15) 提供完整 dj_stream 目录的8个视频以及5个LUT、1个CSV，保留原目录结构，不转码。

详见 [文件下载索引](Media/README.md) 与 [逐文件 SHA256 清单](Media/manifest.json)。其中只有比较报告指定的四份原片属于3,399帧分析范围，其余文件按提供内容完整上传。

Release 同时提供四套独立源码压缩包和总包。源码、配置与对比表可直接在本仓库浏览；大型原视频保存在 Release 资产中。

## 编译与复现

各工程的 EXPERIMENT_REPORT.md、build.bat 和验证脚本包含具体命令。当前 Windows 构建面向 Visual Studio 2026 Community/v145，其他安装路径和工具集需调整。测试需要 Python 3.10+、FFmpeg，以及本地 ParkScene YUV 数据。

公共分析入口为 [Comparison/analyze_video.py](Comparison/analyze_video.py)：

```powershell
python Comparison/analyze_video.py --input video.mp4 --decoder HM_16.20_DJ_Action6/bin/TAppDecoder_camera.exe --output analysis/video
```

原始 HM 版权和许可保留在各工程 HM-16.20/COPYING，根目录另附 COPYING.HM。实验复现工具配置与搜索限制，不复制 DJI 私有编码算法、AQ 或码控。
