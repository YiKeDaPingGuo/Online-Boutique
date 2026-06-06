# GDN 与智能运维 Agent 接口说明

## 1. 模块定位

本目录中的 GDN 模块负责 **异常检测与异常指标定位**，智能体开发同学可以将其作为一个可调用的检测工具使用。

GDN 不负责直接执行修复动作。它输出：

1. 当前时间窗口是否异常；
2. 异常分数与阈值；
3. 异常贡献最高的指标；
4. 可供 Agent 继续查询日志、Pod 状态、Prometheus 指标的候选服务。

推荐职责划分：

| 模块 | 责任 |
|------|------|
| GDN | 发现异常、输出异常分数、定位异常指标 |
| Agent | 读取 GDN 结果、结合 Prometheus / 日志 / kubectl 进一步诊断 |
| Remediation | 在人工确认或策略允许时执行重启、扩容、删除故障注入等动作 |

---

## 2. 论文方法与 Agent 的关系

GDN 论文的核心思想是：将多维监控指标看作图节点，学习指标之间的依赖关系，并预测下一时刻指标值。当真实值与预测值偏差过大时，判定为异常。

在智能体场景中，可以对应为：

```text
Prometheus 指标  ->  GDN 异常检测  ->  Top 异常指标  ->  Agent 根因分析  ->  运维建议/动作
```

论文能力到智能体能力的映射：

| GDN 论文能力 | Agent 中的作用 |
|--------------|----------------|
| Sensor Embedding | 建模不同指标的行为特征 |
| Graph Structure Learning | 学习微服务指标间依赖关系 |
| Graph Attention Forecasting | 预测正常情况下指标应有的表现 |
| Deviation Scoring | 判断当前系统是否异常 |
| Top anomalous features | 为 Agent 提供根因定位线索 |

---

## 3. 文件接口总览

当前推荐使用 **文件接口**，不需要启动 HTTP 服务。

### 3.1 输入文件

路径：

```text
experiment/GDN/data/
```

输入文件：

| 文件 | 说明 |
|------|------|
| `normal_train.csv` | 正常训练数据 |
| `normal_valid.csv` | 正常验证数据，用于确定阈值 |
| `fault_cpu_frontend.csv` | CPU 故障测试数据 |
| `fault_delay_cart.csv` | 网络延迟故障测试数据 |
| `fault_kill_product.csv` | Pod Kill 故障测试数据 |
| `experiment-log.md` | 故障注入时间与结束时间，用于生成 attack 标签 |

当前有效特征为 22 维：

```text
11 个服务 × cpu/mem
```

说明：当前 Minikube 环境未暴露 pod 级 `container_network_*` 指标，因此 `net_rx/net_tx` 已在预处理阶段自动剔除。

### 3.2 运行命令

在 `Online-Boutique` 根目录执行：

```powershell
cd D:\soft\AndroidStudioProjects\Online-Boutique\experiment\GDN

python scripts\prepare_gdn_data.py
python scripts\run_gdn_reproduction.py --epochs 120
```

`prepare_gdn_data.py` 默认会：

- 读取 `experiment-log.md` 中的故障时间；
- 将故障结束后 2 分钟恢复期也标记为 `attack=1`；
- 自动剔除全空特征；
- 生成 GDN 需要的 `train.csv`、`test.csv`、`list.txt`。

### 3.3 输出文件

路径：

```text
experiment/GDN/results/
```

输出文件：

| 文件 | 说明 |
|------|------|
| `gdn_lightweight_scores.csv` | 每个测试时间窗口的异常分数和预测结果 |
| `gdn_lightweight_top_features.csv` | 平均异常贡献最高的 Top 指标 |

---

## 4. 输出字段说明

### 4.1 `gdn_lightweight_scores.csv`

示例：

```csv
timestamp,score,threshold,prediction,attack
5,77.26091003417969,5.154173851013184,1,1
6,76.62159729003906,5.154173851013184,1,1
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `timestamp` | int / str | 测试窗口索引；当前轻量实现中为窗口偏移后的序号 |
| `score` | float | GDN 计算得到的异常分数 |
| `threshold` | float | 验证集最大异常分数，作为异常阈值 |
| `prediction` | int | GDN 预测标签，`1` 表示异常，`0` 表示正常 |
| `attack` | int | 实验标注标签，`1` 表示故障影响期，`0` 表示正常期 |

Agent 接入时最重要的判断规则：

```text
prediction == 1  =>  GDN 检测到异常
score > threshold  =>  异常分数超过阈值
```

### 4.2 `gdn_lightweight_top_features.csv`

示例：

```csv
rank,feature,mean_score
1,emailservice_mem,1628.57568359375
2,cartservice_mem,108.40736389160156
3,recommendationservice_mem,76.93926239013672
```

字段说明：

| 字段 | 类型 | 说明 |
|------|------|------|
| `rank` | int | 异常贡献排名 |
| `feature` | str | 指标名称，格式为 `{service}_{metric}` |
| `mean_score` | float | 该指标的平均异常贡献分数 |

Agent 可根据 `feature` 拆分出服务名与指标类型：

```text
emailservice_mem        -> service=emailservice, metric=mem
cartservice_mem         -> service=cartservice, metric=mem
productcatalogservice_cpu -> service=productcatalogservice, metric=cpu
```

---

## 5. 当前实验结果

最新 GDN 结果：

```text
precision: 0.8462
recall:    1.0000
f1:        0.9167
threshold: 5.154174
```

Top 异常指标：

| rank | feature | mean_score |
|------|---------|------------|
| 1 | `emailservice_mem` | 1628.58 |
| 2 | `cartservice_mem` | 108.41 |
| 3 | `recommendationservice_mem` | 76.94 |
| 4 | `productcatalogservice_mem` | 35.06 |
| 5 | `paymentservice_mem` | 29.44 |
| 6 | `adservice_mem` | 24.00 |
| 7 | `frontend_cpu` | 23.36 |
| 8 | `emailservice_cpu` | 20.86 |
| 9 | `currencyservice_mem` | 20.40 |
| 10 | `frontend_mem` | 18.88 |

---

## 6. Agent 调用逻辑建议

### 6.1 最小接入流程

Agent 可以按以下逻辑调用 GDN：

```text
1. 定时或收到告警后运行 GDN 脚本
2. 读取 results/gdn_lightweight_scores.csv
3. 判断最后一行或最近 N 行中是否存在 prediction=1
4. 若异常，读取 results/gdn_lightweight_top_features.csv
5. 根据 Top feature 推断候选服务
6. 调用 Prometheus / kubectl logs / kubectl get pods 进一步确认
7. 输出诊断结论和修复建议
```

### 6.2 Python 读取示例

```python
from pathlib import Path
import pandas as pd

GDN_DIR = Path("D:/soft/AndroidStudioProjects/Online-Boutique/experiment/GDN")

scores = pd.read_csv(GDN_DIR / "results/gdn_lightweight_scores.csv")
top_features = pd.read_csv(GDN_DIR / "results/gdn_lightweight_top_features.csv")

recent = scores.tail(5)
is_anomaly = (recent["prediction"] == 1).any()

if is_anomaly:
    candidates = top_features.head(5)["feature"].tolist()
    print("GDN 检测到异常")
    print("候选异常指标:", candidates)
else:
    print("GDN 未检测到异常")
```

### 6.3 候选服务提取示例

```python
def feature_to_service(feature: str) -> str:
    for suffix in ["_cpu", "_mem", "_net_rx", "_net_tx"]:
        if feature.endswith(suffix):
            return feature[: -len(suffix)]
    return feature

services = [feature_to_service(f) for f in top_features.head(5)["feature"]]
services = list(dict.fromkeys(services))
print(services)
```

输出示例：

```text
["emailservice", "cartservice", "recommendationservice", "productcatalogservice", "paymentservice"]
```

---

## 7. Agent 可继续调用的工具建议

智能体开发同学可以基于 GDN 输出进一步调用以下工具。

### 7.1 查询 Prometheus

```python
def execute_promql(query: str) -> str:
    ...
```

示例 PromQL：

```promql
sum(rate(container_cpu_usage_seconds_total{namespace="onlineboutique", pod=~"cartservice.*"}[1m]))
sum(container_memory_working_set_bytes{namespace="onlineboutique", pod=~"cartservice.*"})
```

### 7.2 查询 Pod 状态

```powershell
kubectl get pods -n onlineboutique
kubectl describe pod <pod-name> -n onlineboutique
```

### 7.3 查询服务日志

```powershell
kubectl logs deploy/cartservice -n onlineboutique --tail=100
kubectl logs deploy/productcatalogservice -n onlineboutique --tail=100
```

### 7.4 修复建议

默认建议只输出，不自动执行：

```powershell
kubectl rollout restart deployment/<service> -n onlineboutique
```

如需自动执行，建议增加人工确认或白名单策略。

---

## 8. 推荐给 Agent 的提示词片段

智能体可以把下面内容加入 system prompt 或工具说明中：

```text
GDN 是当前系统的异常检测工具。它基于 Prometheus 多维指标学习服务之间的依赖关系，并通过预测误差判断异常。
当 GDN 输出 prediction=1 时，说明系统指标已经偏离正常模式。
请优先读取 gdn_lightweight_top_features.csv 中排名靠前的 feature，将 feature 拆分为 service 与 metric，
再调用 Prometheus 查询、kubectl logs 和 kubectl describe 获取证据，最后给出根因分析和修复建议。
不要仅根据单一 CPU 阈值判断故障，应综合 GDN score、Top feature、Pod 状态和日志。
```

---

## 9. 当前限制

1. 当前为离线/批处理接口，不是实时流式检测。
2. 训练集较短，结果适合实验复现，不代表生产可用精度。
3. 当前 Minikube 未暴露 pod 级网络指标，因此只使用 cpu/mem。
4. `timestamp` 当前为窗口索引，而非真实时间戳。如 Agent 需要真实时间，可在后续版本中将 `prepare_gdn_data.py` 保留原始时间列映射。
5. 自动修复动作应谨慎，建议先作为“修复建议”输出。

---

## 10. 交付给智能体开发同学的最小文件清单

```text
experiment/GDN/
├── GDN-AGENT-INTERFACE.md
├── experiment-log.md
├── scripts/
│   ├── prepare_gdn_data.py
│   └── run_gdn_reproduction.py
├── data/
│   ├── normal_train.csv
│   ├── normal_valid.csv
│   ├── fault_cpu_frontend.csv
│   ├── fault_delay_cart.csv
│   └── fault_kill_product.csv
└── results/
    ├── gdn_lightweight_scores.csv
    └── gdn_lightweight_top_features.csv
```

---

## 11. 一句话总结

GDN 模块为智能运维 Agent 提供 **异常检测结果和根因候选指标**；Agent 不需要理解或重写 GDN 算法，只需要读取 `scores.csv` 判断是否异常，再读取 `top_features.csv` 选择后续排查对象。

