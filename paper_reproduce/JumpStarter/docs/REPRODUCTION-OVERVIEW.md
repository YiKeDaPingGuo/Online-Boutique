# JumpStarter Online Boutique 复现总览

## 1. 文档定位

本文档是本次 JumpStarter 复现实验的入口文档，重点说明环境配置、数据目录、预处理命令、detector 运行命令和主要结果。

相关文档分工如下：

| 文档 | 作用 |
| --- | --- |
| `docs/REPRODUCTION-OVERVIEW.md` | 复现入口、环境配置、运行命令、结果摘要 |
| `docs/PROJECT-JUMPSTARTER.md` | 实验设计、数据语义、标签规则、窗口选择、局限说明 |
| `docs/JUMPSTARTER-AGENT-INTERFACE.md` | 面向智能运维 agent 的离线文件接口说明 |
| `mydata/README.md` | 数据目录索引和脚本说明 |

## 2. 复现目标

原论文为：

```text
Jump-Starting Multivariate Time Series Anomaly Detection for Online Service Systems
USENIX ATC 2021
```

本项目将 JumpStarter 的多变量时间序列异常检测流程迁移到：

```text
Online Boutique + Kubernetes/Minikube + Prometheus + Chaos Mesh
```

JumpStarter 的核心思想是使用 Compressed Sensing 对多维指标窗口进行重构，再根据原始信号与重构信号之间的差异计算 anomaly score。

## 3. Environment Setup

环境分成两层：

| 目的 | 所需环境 |
| --- | --- |
| 直接运行已处理数据上的 JumpStarter detector | Python/Conda 环境 |
| 重新采集指标和注入故障 | Kubernetes/Minikube、Online Boutique、Prometheus/Grafana、Chaos Mesh |

### 3.1 Conda 环境

推荐使用项目中的环境文件：

```text
environment-jumpstarter.yml
```

在 JumpStarter 根目录执行：

```powershell
conda env create -f environment-jumpstarter.yml
conda activate jumpstarter
```

主要依赖版本：

| 依赖 | 版本 |
| --- | --- |
| Python | 3.7 |
| numpy | 1.18.1 |
| pandas | 1.0.2 |
| scipy | 1.4.1 |
| scikit-learn | 0.23.2 |
| matplotlib | 3.1.3 |
| PyYAML | 5.3.1 |
| tqdm | 4.43.0 |
| cvxpy | 1.0.28 |

在 Windows 上运行 detector 前建议设置：

```powershell
$env:PYTHONNOUSERSITE='1'
```

这样可以避免误加载用户目录下版本不兼容的 Python 包。

### 3.2 requirement.txt

`requirement.txt` 保留为原项目依赖参考。本次复现更推荐使用 `environment-jumpstarter.yml`，因为 JumpStarter 对 `numpy`、`scipy`、`scikit-learn`、`cvxpy` 等老版本依赖比较敏感。

### 3.3 Online Boutique 采集环境

采集数据时使用的系统栈如下：

| 组件 | 作用 |
| --- | --- |
| Online Boutique | 被测微服务系统 |
| Kubernetes / Minikube | 部署环境 |
| Prometheus | 指标采集 |
| Grafana | 指标观察 |
| Chaos Mesh | 故障注入 |

故障注入配置和本地运行脚本位于：

```text
mydata/scripts/chaos-exp/
```

当前仓库已经保留处理后的数据，因此只想复跑 detector 时，不需要重新搭建 Kubernetes 环境。

## 4. 数据目录

本次复现数据位于：

```text
mydata/
```

主要目录：

| 路径 | 说明 |
| --- | --- |
| `mydata/raw_self/` | 自己采集的 Online Boutique 原始 CSV |
| `mydata/scripts/` | 采集、预处理、打标、分析脚本 |
| `mydata/processed/full_log_based/` | 55 指标 log-based 中间结果 |
| `mydata/processed/signal_log_based/` | 44 指标 log-based 主结果 |
| `mydata/processed/signal_observed/` | 44 指标 observed-impact 对照结果 |
| `mydata/external/` | 同学数据和对应处理结果 |
| `mydata/experiment-log.md` | 故障注入时间记录 |
| `mydata/tuning_report.md` | 调参和结果记录 |

自己采集的故障类型：

| 文件 | 故障类型 | 目标服务 |
| --- | --- | --- |
| `fault_cpu_frontend.csv` | CPU stress | `frontend` |
| `fault_mem_recommendation.csv` | Memory stress | `recommendationservice` |
| `fault_delay_cart_repeat_500ms.csv` | repeated 500ms network delay | `cartservice` |
| `fault_kill_product_repeat.csv` | repeated pod kill | `productcatalogservice` |

采样间隔：

```text
30 秒 / 点
```

## 5. 数据版本

当前主要保留两套标签语义：

| 数据版本 | 路径 | `label=1` 含义 | 用途 |
| --- | --- | --- | --- |
| log-based | `mydata/processed/signal_log_based/` | 处于故障注入或预期影响窗口内 | 报告主结果 |
| observed-impact | `mydata/processed/signal_observed/` | 已经出现可观测的服务指标影响 | 对照解释 |

log-based 主文件：

```text
mydata/processed/signal_log_based/data/test_all_signal.csv
mydata/processed/signal_log_based/label/test_all_signal.csv
mydata/processed/signal_log_based/configs/test_all_signal_w10.yml
```

observed-impact 主文件：

```text
mydata/processed/signal_observed/data/test_all_signal_observed.csv
mydata/processed/signal_observed/label/test_all_signal_observed.csv
mydata/processed/signal_observed/configs/test_all_signal_observed_w10.yml
```

## 6. 重新生成数据

在 JumpStarter 根目录执行：

```powershell
python mydata\scripts\process_mydata.py
python mydata\scripts\make_signal_dataset.py
python mydata\scripts\make_observed_signal_dataset.py
```

脚本作用：

| 脚本 | 输出 |
| --- | --- |
| `process_mydata.py` | `processed/full_log_based/` |
| `make_signal_dataset.py` | `processed/signal_log_based/` |
| `make_observed_signal_dataset.py` | `processed/signal_observed/` |
| `make_no_delay_dataset.py` | no-delay 对照数据 |
| `analyze_scores.py` | `mydata/score_analysis.csv` |

## 7. Run Detector

### 7.1 log-based 主实验

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_all_signal_w10.yml
```

输出目录：

```text
mydata/processed/signal_log_based/result/
```

主要输出：

```text
test_all_signal_w10_score.txt
test_all_signal_w10_rec.txt
```

### 7.2 observed-impact 对照实验

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_observed\configs\test_all_signal_observed_w10.yml
```

输出目录：

```text
mydata/processed/signal_observed/result/
```

## 8. 窗口设置

当前主配置使用：

```text
reconstruct.window = 10
detect.window = 5
```

由于每个点代表 30 秒：

| 点数 | 实际时间 |
| ---: | ---: |
| 5 | 2.5 分钟 |
| 10 | 5 分钟 |
| 20 | 10 分钟 |
| 40 | 20 分钟 |

选择 5 分钟重构窗口的原因是：当前故障持续时间较短，训练数据规模较小，长窗口容易覆盖过多无关上下文。

## 9. 主要结果

报告采用的 log-based 主结果：

```text
Precision: 61.65
Recall:    95.35
F1_score:  74.89
```

observed-impact 对照结果：

```text
Precision: 53.26
Recall:    100.00
F1_score:  69.50
```

这些结果适合作为课程复现实验结果，不代表生产环境可用精度。当前正常训练数据和故障重复轮数仍然有限。

## 10. 注意事项

1. `test_all_signal.csv` 是多个实验文件拼接得到的，不是一条真实连续生产时间线。
2. 推荐的 `w10` 配置中，文件边界与 10 点重构窗口对齐，因此重构窗口本身不会跨文件边界，但检测窗口仍可能引用边界附近历史分数。
3. log-based 和 observed-impact 的 `label=1` 含义不同，写报告或对比实验时不要混用。
4. JumpStarter 输出 anomaly score 和重构信号，不直接给出根因服务。

