# JumpStarter 与智能运维 Agent 接口说明

## 0. 文档定位

本文档只说明 JumpStarter 如何以离线文件形式向智能运维 agent 暴露检测结果。环境安装、数据处理和 detector 运行命令见：

```text
docs/REPRODUCTION-OVERVIEW.md
```

## 1. 模块定位

JumpStarter 模块负责对 Online Boutique 的多服务监控指标进行异常检测。它面向 agent 提供的是离线文件接口，而不是实时 HTTP 服务。

JumpStarter 的职责：

1. 读取处理后的多变量时间序列；
2. 按滑动窗口重构信号；
3. 输出每个时间点的 anomaly score；
4. 输出检测评估结果；
5. 为 agent 提供是否异常的判断依据。

Agent 的职责：

1. 调用 JumpStarter 或读取其结果文件；
2. 判断最近窗口是否异常；
3. 结合 Prometheus、kubectl、日志继续排查；
4. 输出根因分析和修复建议；
5. 在有人工确认或策略授权时执行修复动作。

推荐职责划分：

| 模块 | 责任 |
| --- | --- |
| JumpStarter | 异常检测、输出 anomaly score |
| Agent | 读取检测结果、关联服务和指标、继续诊断 |
| Remediation | 根据策略执行重启、扩容、回滚等动作 |

## 2. 最小接入流程

Agent 可以按下面流程调用 JumpStarter：

```text
1. 准备或更新 processed 数据
2. 运行 detector/run_detector.py
3. 读取 result/*_score.txt
4. 读取 label/*.csv 或外部时间戳映射
5. 判断最近 N 个点是否异常
6. 若异常，查询 Prometheus / kubectl / logs
7. 输出诊断结论和修复建议
```

当前推荐配置仍为：

```text
mydata/processed/signal_log_based/configs/test_all_signal_w10.yml
```

具体环境创建、数据重生成和 detector 运行命令统一见：

```text
docs/REPRODUCTION-OVERVIEW.md#7-run-detector
```

## 3. 输入文件

### 3.1 JumpStarter 输入

推荐输入目录：

```text
mydata/processed/signal_log_based/
```

核心文件：

| 文件 | 说明 |
| --- | --- |
| `data/test_all_signal.csv` | 处理后的 44 维指标数据，无 header |
| `label/test_all_signal.csv` | 与 data 同行数的 0/1 标签 |
| `configs/test_all_signal_w10.yml` | 5 分钟窗口配置 |
| `metadata/summary.csv` | 数据组成、行数、异常点统计 |
| `metadata/feature_columns.txt` | 44 个输入指标名称 |

当前数据规模：

```text
rows: 420
features: 44
positive labels: 86
sampling interval: 30 seconds
window: 10 points = 5 minutes
```

标签语义：

```text
label=1 表示采样点处于故障注入或预期故障影响窗口内。
label=0 表示采样点不在人工标注的故障影响窗口内。
```

注意：`label=1` 不等于每个指标在该点一定已经出现明显异常。CPU 和 memory 主要标注故障注入活跃期间；network delay 和 pod kill 因为存在恢复滞后，因此使用扩展影响窗口。

### 3.2 拼接边界风险

当前 `data/test_all_signal.csv` 由多个实验文件拼接得到：

```text
normal_valid
fault_cpu_frontend
fault_mem_recommendation
fault_delay_cart_repeat_500ms
fault_kill_product_repeat
```

JumpStarter 当前实现会把输入矩阵当作一条连续时间序列处理。对于推荐配置 `test_all_signal_w10.yml`：

```text
reconstruct.window = 10
reconstruct.stride = 10
detect.window = 5
detect.stride = 1
```

由于文件边界刚好落在 10 的倍数上，重构窗口本身不跨边界；但检测窗口仍可能跨边界，边界后的采样评分历史也可能引用前一个实验文件。因此 agent 在解释结果时应把 `test_all_signal.csv` 视为离线评估集合，而不是一条真实连续生产时间线。

如果后续要给 agent 提供更严格的接口，建议在预处理阶段保留：

```text
source_file
experiment_id
segment_id
timestamp
```

并在生成窗口时丢弃跨实验边界的窗口。

### 3.3 指标命名

指标名格式：

```text
{service}_{metric}
```

示例：

```text
frontend_cpu
frontend_mem
frontend_request_rate
frontend_error_rate
cartservice_cpu
cartservice_request_rate
productcatalogservice_error_rate
```

当前推荐版本去掉了 `_latency` 列，保留：

```text
cpu, mem, request_rate, error_rate
```

## 4. 输出文件

JumpStarter 运行后输出到：

```text
mydata/processed/signal_log_based/result/
```

主要文件：

| 文件 | 说明 |
| --- | --- |
| `test_all_signal_w10_score.txt` | 每个时间点的异常分数 |
| `test_all_signal_w10_rec.txt` | 重构后的时间序列 |

控制台会输出：

```text
Precision
Recall
F1_score
```

报告采用的主结果：

```text
Precision: 61.65
Recall:    95.35
F1_score:  74.89
```

说明：这是重构 observed-impact 打标版本之前的 log-based 历史主结果；当前文件路径已更新到 `mydata/processed/signal_log_based/`。

## 5. Score 文件解释

`*_score.txt` 是一列数值，每一行对应一个时间点或检测位置的 anomaly score。

基本判断规则：

```text
score 越高，越可能异常
```

当前项目里的评估函数会自动搜索阈值并计算 F1。Agent 如果只读取文件结果，建议使用以下策略之一：

| 策略 | 说明 |
| --- | --- |
| 使用评估函数阈值 | 适合离线实验，有 label 时使用 |
| 使用验证集分位数阈值 | 适合无 label 的近实时检测 |
| 使用最近 N 点趋势 | 适合告警降噪 |

推荐 agent 最小规则：

```text
recent_scores = 最近 5 个 score
if max(recent_scores) > threshold:
    判断为异常
else:
    判断为正常
```

如果暂时没有稳定阈值，不建议让 agent 自动修复，只建议输出“需要进一步排查”。

## 6. Python 读取示例

```python
from pathlib import Path
import numpy as np
import pandas as pd

BASE = Path("mydata/processed/signal_log_based")

scores = np.loadtxt(BASE / "result/test_all_signal_w10_score.txt")
labels = np.loadtxt(BASE / "label/test_all_signal.csv", delimiter=",")
features = (BASE / "metadata/feature_columns.txt").read_text(encoding="utf-8").splitlines()

recent_scores = scores[-5:]
print("recent_scores:", recent_scores)
print("feature_count:", len(features))
```

如果需要复用项目评估函数：

```python
import sys
import numpy as np

sys.path.append(".")
from utils.metrics import evaluation

labels = np.loadtxt("mydata/processed/signal_log_based/label/test_all_signal.csv", delimiter=",")
scores = np.loadtxt("mydata/processed/signal_log_based/result/test_all_signal_w10_score.txt")

precision, recall, f1, threshold = evaluation(labels, scores)
print(precision, recall, f1, threshold)
```

## 7. 服务名提取

Agent 可以从指标名中提取服务名和指标类型。

```python
def split_feature(feature: str):
    suffixes = ["_request_rate", "_error_rate", "_cpu", "_mem", "_latency"]
    for suffix in suffixes:
        if feature.endswith(suffix):
            return feature[:-len(suffix)], suffix[1:]
    return feature, "unknown"

service, metric = split_feature("cartservice_request_rate")
print(service, metric)
```

输出：

```text
cartservice request_rate
```

## 8. Agent 后续诊断建议

JumpStarter 只能说明指标模式异常，不能单独证明根因。Agent 需要继续查证。

### 8.1 查询 Prometheus

CPU：

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="onlineboutique", pod=~"frontend.*"}[1m]))
```

Memory：

```promql
sum(container_memory_working_set_bytes{namespace="onlineboutique", pod=~"recommendationservice.*"})
```

Request rate：

```promql
sum(rate(http_requests_total{namespace="onlineboutique", service="cartservice"}[2m]))
```

Error rate：

```promql
sum(rate(http_requests_total{namespace="onlineboutique", service="frontend", status=~"5.."}[2m]))
```

实际 PromQL 需要按当前 Prometheus 指标名调整。

### 8.2 查询 Pod 状态

```powershell
kubectl get pods -n onlineboutique
kubectl describe pod <pod-name> -n onlineboutique
```

### 8.3 查询服务日志

```powershell
kubectl logs deploy/frontend -n onlineboutique --tail=100
kubectl logs deploy/cartservice -n onlineboutique --tail=100
kubectl logs deploy/productcatalogservice -n onlineboutique --tail=100
```

### 8.4 检查 Chaos Mesh 残留

```powershell
kubectl get stresschaos -n chaos-mesh
kubectl get networkchaos -n chaos-mesh
kubectl get podchaos -n chaos-mesh
```

## 9. 修复建议输出格式

Agent 输出建议时可以使用下面格式：

```json
{
  "status": "anomaly_detected",
  "detector": "JumpStarter",
  "score": 0.123,
  "threshold": 0.08,
  "suspected_services": ["frontend", "cartservice"],
  "suspected_metrics": ["request_rate", "error_rate"],
  "evidence": [
    "JumpStarter score exceeded threshold in recent window",
    "frontend_error_rate increased",
    "cartservice_request_rate decreased"
  ],
  "recommended_actions": [
    "Check cartservice pod status",
    "Check frontend and cartservice logs",
    "Verify whether Chaos Mesh experiment is still running"
  ],
  "auto_remediation_allowed": false
}
```

默认建议：

```text
只输出修复建议，不自动执行修复命令。
```

## 10. 可选封装接口

后续可以增加一个轻量封装脚本，例如：

```text
agent_tools/run_jumpstarter_check.py
```

建议 CLI：

```powershell
python agent_tools/run_jumpstarter_check.py `
  --config mydata/processed/signal_log_based/configs/test_all_signal_w10.yml `
  --score mydata/processed/signal_log_based/result/test_all_signal_w10_score.txt `
  --feature-list mydata/processed/signal_log_based/metadata/feature_columns.txt `
  --recent 5
```

建议输出：

```json
{
  "is_anomaly": true,
  "max_recent_score": 0.123,
  "recent_window": 5,
  "score_file": "mydata/processed/signal_log_based/result/test_all_signal_w10_score.txt"
}
```

## 11. 当前限制

1. 当前接口是离线文件接口，不是实时流式服务；
2. `score.txt` 默认没有真实时间戳，agent 需要额外维护时间戳映射；
3. JumpStarter 当前输出不包含 top feature 定位；
4. 阈值策略仍依赖实验评估或验证集统计；
5. 自动修复必须谨慎，建议先做人机协同。

## 12. 一句话总结

JumpStarter 给 agent 提供“当前多服务指标是否偏离正常模式”的检测信号；agent 需要在此基础上结合 Prometheus、Pod 状态和日志，完成根因分析与修复建议。
