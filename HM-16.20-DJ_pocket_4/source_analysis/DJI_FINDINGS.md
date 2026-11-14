# DJI 原始码流全片核对

源文件：`C:/Users/shaol/Downloads/DJI_20260429163710_0019_D.MP4`。

完整提取视频轨，不重编码，使用 HM 逐块解码全部 **328 帧**。原片为 Main10、3840×2160、60000/1001 fps，包含 11 个 I 帧、317 个 P 帧。这里只分析现有码流；新增编码实验均为用户要求的 8 bit。

## Inter8 的结论

**原码流实际使用了 Inter CU8，但并非只使用或只支持 Inter8。**

| 结构 | 实际数量 |
| --- | ---: |
| Inter CU16（含 Skip） | 10,181,729 |
| Inter CU8（含 Skip） | 6 |
| 16×16 Inter PU | 10,099,484 |
| 16×8 Inter PU | 56,612 |
| 8×16 Inter PU | 107,878 |
| 8×8 Inter PU，所属 CU8 | 6 |

六个 8×8 PU 都属于真正的 CU8，并非把 CU16 内的矩形 PU 宽度误称为 Inter8。CSV 只分析前 10 帧，遗漏了这些极少见的结构；据此前 10 帧就禁用 Inter8 是上一版代码的错误限制。

| 解码序号（从 0 开始） | POC | 类型 | Inter CU8 数量 |
| ---: | ---: | --- | ---: |
| 118 | 28 | P | 1 |
| 170 | 20 | P | 1 |
| 222 | 12 | P | 1 |
| 273 | 3 | P | 1 |
| 278 | 8 | P | 1 |
| 290 | 20 | P | 1 |

POC 在随机接入周期中重置，因此定位时同时使用全局解码序号和 POC。计数来自最终解码叶 CU 和实际 PU 几何，不是编码器临时候选。原片使用 Inter8 是已观察事实；硬件完整支持集不能仅由某个模式未出现推断。

## Intra8 / 四个亮度 TU4 的结论

原片的 **297,682 个 Intra CU8 均为一个 8×8 PU、一个亮度 TU8**，没有观察到 Intra CU8 下的 TU4。具有非零亮度 CBF 的 CU8/TU8 有 281,069 个。

所有实际 SPS 的 `max_transform_hierarchy_depth_intra` 语法值为 0；在这里的 CU8 / 2N×2N Intra 结构下不允许继续下分为四个 TU4。`log2_min_luma_transform_block_size_minus2=0` 只说明总体最小 TU 为 4，不能证明 Intra CU8 可以下分。也不能把色度 TU4 当成亮度 TU4。

因此，**这份原码流未使用、也未在其现有 CU8/单 PU8 结构中开放四 TU4**；这不等同于证明 DJI 硬件没有其他编码配置可以支持。为用户新增需求，当前 HM 另提供可选四 TU4 配置，默认模仿配置仍保持 Intra8/TU8。

## 可重复证据

- `source_findings.json`：完整统计与原片 SHA256。
- `tools_all_frames.jsonl`：逐帧 CU/PU/TU 结构统计。
- `cu8_tu_and_inter_per_picture.csv`：逐帧 CU8 / TU4 核对表。
- `headers_trace.log`：FFmpeg 独立参数集语法跟踪。
- `decoder.log`：328 帧 HM 解码日志。

重新分析：`python analyze_dji.py`。提取的 `dji_source.265` 是原视频轨的 Annex B 表示，没有重新编码。
