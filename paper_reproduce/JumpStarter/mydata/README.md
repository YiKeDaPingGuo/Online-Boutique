# mydata 数据目录索引

这个目录已经按数据来源和处理阶段重构。当前结构把你自己的原始数据、处理脚本、处理结果和同学数据分开，避免不同窗口、不同标签语义的数据混在一起。

## 1. 目录总览

| 路径 | 类型 | 说明 |
| --- | --- | --- |
| `raw_self/` | 原始数据 | 自己采集的 Online Boutique CSV，带 `timestamp` 和 header |
| `scripts/` | 脚本 | 采集、预处理、打标、分析脚本 |
| `processed/full_log_based/` | 中间结果 | 55 指标，log-based 标签，供后续处理使用 |
| `processed/signal_log_based/` | 主结果 | 44 指标，log-based 标签 |
| `processed/signal_observed/` | 新结果 | 44 指标，observed-impact 标签 |
| `external/ll_data/` | 同学数据 | 第一版同学 CSV 数据及处理结果 |
| `external/ll_data_new/` | 同学数据 | 第二版同学 CSV/JSON 数据及处理结果 |
| `external/partner_hyx_data/` | 同学数据 | HYX 同学的 PKL 数据及处理结果 |
| `experiment-log.md` | 实验日志 | 自己的故障注入时间、目标服务、故障类型记录 |
| `tuning_report.md` | 调参记录 | 旧版调参结果总结 |
| `score_analysis.csv` | 分析结果 | 旧版 score 离线分析结果，可重新生成 |

## 2. 本人收集原始 CSV

原始文件都在：

```text
mydata/raw_self/
```

| 文件 | 类型 | 行数 | 原始列数 | 说明 |
| --- | --- | ---: | ---: | --- |
| `normal_train.csv` | normal | 120 | 56 | 正常训练数据 |
| `normal_valid.csv` | normal | 60 | 56 | 正常验证/测试前置数据 |
| `fault_cpu_frontend.csv` | fault | 100 | 56 | `frontend` CPU stress |
| `fault_mem_recommendation.csv` | fault | 100 | 56 | `recommendationservice` memory stress |
| `fault_delay_cart_repeat_500ms.csv` | fault | 80 | 56 | `cartservice` repeated 500ms network delay |
| `fault_kill_product_repeat.csv` | fault | 80 | 56 | `productcatalogservice` repeated pod kill |

原始格式：

```text
timestamp + 11 services x 5 metrics
```

指标类型：

```text
cpu, mem, request_rate, latency, error_rate
```

## 3. 脚本分类

脚本都在：

```text
mydata/scripts/
```

| 脚本 | 作用 | 输入 | 输出 |
| --- | --- | --- | --- |
| `collect_ob_metrics.py` | 从 Prometheus 采集原始指标 | Prometheus | `raw_self/*.csv` 或指定输出 |
| `process_mydata.py` | 生成 55 指标 log-based 标签版本 | `raw_self/*.csv` | `processed/full_log_based/` |
| `make_signal_dataset.py` | 去掉 latency，生成 44 指标 log-based 版本 | `processed/full_log_based/` | `processed/signal_log_based/` |
| `make_observed_signal_dataset.py` | 根据实际指标变化重新打标 | `raw_self/*.csv` | `processed/signal_observed/` |
| `make_no_delay_dataset.py` | 旧版 no-delay 对照 | `processed/full_log_based/` | `processed/no_delay_legacy/` |
| `analyze_scores.py` | 分析已有 score 和 label | `processed/*/result` | `score_analysis.csv` |

推荐重新生成顺序：

```powershell
python mydata\scripts\process_mydata.py
python mydata\scripts\make_signal_dataset.py
python mydata\scripts\make_observed_signal_dataset.py
```

## 4. 标签版本分类

当前有两套主要标签语义。

| 目录 | 标签类型 | label=1 的含义 | 异常点 | 推荐用途 |
| --- | --- | --- | ---: | --- |
| `processed/signal_log_based/` | log-based | 处于故障注入或预期影响窗口 | 86 / 420 | 和实验日志严格对应，适合说明故障注入时间 |
| `processed/signal_observed/` | observed-impact | 指标已经出现明显服务影响 | 98 / 420 | 更贴近 CSV 实际指标变化，适合解释观测异常 |

log-based 主数据：

```text
processed/signal_log_based/data/test_all_signal.csv
processed/signal_log_based/label/test_all_signal.csv
```

observed-impact 主数据：

```text
processed/signal_observed/data/test_all_signal_observed.csv
processed/signal_observed/label/test_all_signal_observed.csv
```

observed-impact 详细异常段：

```text
processed/signal_observed/metadata/observed_label_segments.csv
```

## 5. 窗口大小分类

采样间隔为 30 秒。

| 窗口点数 | 实际时间 |
| ---: | ---: |
| 5 | 2.5 分钟 |
| 10 | 5 分钟 |
| 15 | 7.5 分钟 |
| 20 | 10 分钟 |
| 40 | 20 分钟 |

你自己的主数据配置：

| 目录 | 配置命名 | reconstruct.window | detect.window | 说明 |
| --- | --- | ---: | ---: | --- |
| `processed/signal_log_based/` | `*_signal.yml` | 20 | 10 | 早期长窗口对照 |
| `processed/signal_log_based/` | `*_signal_w10.yml` | 10 | 5 | 当前 log-based 主配置 |
| `processed/signal_observed/` | `*_observed_w10.yml` | 10 | 5 | 当前 observed-impact 主配置 |

注意：文件名里的 `w10` 表示 10 个采样点，不是 10 分钟。

## 6. 当前推荐运行命令

log-based 标签：

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_all_signal_w10.yml
```

报告采用的主结果：

```text
Precision: 61.65
Recall:    95.35
F1_score:  74.89
```

说明：这是重构 observed-impact 打标版本之前的 log-based 历史主结果。当前目录已重构为 `processed/signal_log_based/`，但数据组成和标签语义对应原 `processed_signal/test_all_signal_w10`。

observed-impact 标签：

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_observed\configs\test_all_signal_observed_w10.yml
```

对照运行结果：

```text
Precision: 53.26
Recall:    100.00
F1_score:  69.50
```

## 7. 重构后的目录树

```text
mydata/
|-- raw_self/
|   |-- normal_train.csv
|   |-- normal_valid.csv
|   |-- fault_cpu_frontend.csv
|   |-- fault_mem_recommendation.csv
|   |-- fault_delay_cart_repeat_500ms.csv
|   `-- fault_kill_product_repeat.csv
|-- scripts/
|   |-- collect_ob_metrics.py
|   |-- process_mydata.py
|   |-- make_signal_dataset.py
|   |-- make_observed_signal_dataset.py
|   |-- make_no_delay_dataset.py
|   |-- analyze_scores.py
|   `-- chaos-exp/
|-- processed/
|   |-- full_log_based/
|   |-- signal_log_based/
|   `-- signal_observed/
|-- external/
|   |-- ll_data/
|   |-- ll_data_new/
|   `-- partner_hyx_data/
|-- experiment-log.md
|-- tuning_report.md
|-- score_analysis.csv
`-- README.md
```
