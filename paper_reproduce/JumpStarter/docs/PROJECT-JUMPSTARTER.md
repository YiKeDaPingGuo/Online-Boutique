# Online Boutique + JumpStarter 项目说明

## 0. 文档定位

本文档保留实验设计、数据语义、标签规则、窗口选择和结果解释。环境安装、数据重生成命令和 detector 运行命令统一放在：

```text
docs/REPRODUCTION-OVERVIEW.md
```

## 1. 项目定位

本项目在 Online Boutique 微服务系统上复现 JumpStarter 异常检测流程。JumpStarter 是一种面向在线服务系统的多变量时间序列异常检测方法，核心思想是使用 Compressed Sensing 对滑动窗口中的多维指标进行重构，再根据原始数据与重构数据之间的差异计算异常分数。

在本实验中，JumpStarter 不直接负责故障注入或修复动作。它的职责是：

1. 读取 Prometheus 导出的多服务监控指标；
2. 将指标组织成等间隔多变量时间序列；
3. 对每个时间窗口计算 anomaly score；
4. 根据标签评估 Precision、Recall、F1；
5. 为后续运维 agent 提供异常检测结果。

## 2. 论文与方法

| 项目 | 内容 |
| --- | --- |
| 论文 | Jump-Starting Multivariate Time Series Anomaly Detection for Online Service Systems |
| 会议 | USENIX ATC 2021 |
| 方法 | Compressed Sensing |
| 输入 | 多变量时间序列窗口 |
| 输出 | 每个时间点或窗口的异常分数 |
| 评估指标 | Precision、Recall、F1 |

论文原始场景是大规模在线服务系统。本项目的目标不是完全复刻论文数据集，而是将 JumpStarter 的检测流程迁移到 Online Boutique + Kubernetes + Chaos Mesh 的实验环境中。

## 3. 实验环境概览

本实验的数据采集环境由 Online Boutique、Kubernetes/Minikube、Prometheus/Grafana 和 Chaos Mesh 组成。JumpStarter detector 本身只需要 Python/Conda 环境即可运行已处理好的数据。

完整环境配置和命令见：

```text
docs/REPRODUCTION-OVERVIEW.md#3-environment-setup
```

## 4. 数据采集

### 4.1 正常数据

| 文件 | 行数 | 指标数 | 说明 |
| --- | ---: | ---: | --- |
| `normal_train.csv` | 120 | 55 | 正常训练数据 |
| `normal_valid.csv` | 60 | 55 | 正常验证/测试前置数据 |

采样间隔为 30 秒。原始格式包含：

```text
timestamp + 11 个服务 x 5 类指标
```

五类指标为：

```text
cpu, mem, request_rate, latency, error_rate
```

### 4.2 故障数据

| 文件 | 故障类型 | 目标服务 | 行数 |
| --- | --- | --- | ---: |
| `fault_cpu_frontend.csv` | CPU stress | `frontend` | 100 |
| `fault_mem_recommendation.csv` | Memory stress | `recommendationservice` | 100 |
| `fault_delay_cart_repeat_500ms.csv` | Network delay, 500ms, repeated | `cartservice` | 80 |
| `fault_kill_product_repeat.csv` | Repeated pod kill | `productcatalogservice` | 80 |

详细故障时间记录在：

```text
mydata/experiment-log.md
```

## 5. 数据处理

当前推荐使用的处理版本是：

```text
mydata/processed/signal_log_based/
```

该版本做了以下处理：

1. 去掉 `timestamp`，只保留数值指标；
2. 去掉所有 `_latency` 列；
3. 保留 `cpu/mem/request_rate/error_rate`；
4. 根据 `experiment-log.md` 生成 0/1 标签；
5. 将 `normal_valid` 和所有故障文件拼接成 `test_all_signal.csv`；
6. 生成 JumpStarter 可直接读取的 YAML 配置。

处理后的主数据规模：

| 数据集 | 组成 | 行数 | 指标数 | 异常点 |
| --- | --- | ---: | ---: | ---: |
| `test_all_signal` | normal valid + 4 类故障 | 420 | 44 | 86 |
| `test_no_delay_signal` | 去掉 network delay | 340 | 44 | 52 |

## 6. 标签规则

正常文件全部标为：

```text
label = 0
```

故障文件只在故障注入或预期影响窗口内标为：

```text
label = 1
```

不同故障的标注方式：

| 故障 | 标签窗口 |
| --- | --- |
| CPU stress | `fault_start` 到 `fault_end` |
| Memory stress | `fault_start` 到 `fault_end` |
| Network delay | 故障开始到故障结束后 3-5 分钟 |
| Pod kill | 每次 kill 后约 2 分钟恢复窗口 |

这里的 `label=1` 表示该采样点处于故障注入或预期故障影响时间窗口内，并不保证每个被标为 1 的采样点在所有指标上都已经表现出明显异常。

当前标签逻辑整体清楚、可复现，主要依据故障注入时间窗口自动生成。CPU 与 memory 故障主要标注故障注入活跃期间；network delay 由于存在网络影响和恢复延迟，因此采用扩展窗口；pod kill 属于瞬时故障，因此采用 kill 后 2 分钟作为异常影响窗口。

最终 `test_all_signal.csv` 共 420 行，其中异常点 86 个、正常点 334 个，异常比例约为 20.5%。该比例适合当前小规模人工故障注入实验，但不能直接等同于论文中的大规模生产环境异常比例。

### 6.1 拼接边界注意事项

`test_all_signal.csv` 是由多个实验文件直接拼接得到：

```text
normal_valid
fault_cpu_frontend
fault_mem_recommendation
fault_delay_cart_repeat_500ms
fault_kill_product_repeat
```

这会带来一个重要注意点：如果模型把拼接后的文件当作一条连续时间序列进行滑动窗口处理，窗口可能跨越不同实验文件边界，从而引入不真实的时间上下文。

当前推荐配置 `test_all_signal_w10.yml` 中：

```text
reconstruct.window = 10
reconstruct.stride = 10
detect.window = 5
detect.stride = 1
```

由于各文件边界位于第 60、160、260、340 行，刚好是 10 的倍数，重构窗口本身不会跨文件边界；但检测窗口仍可能跨边界，边界后的采样评分历史也可能引用前一个实验文件。因此当前结果可以作为复现实验结果使用，但在报告中需要说明这一限制。

更严格的做法是：每个实验文件单独生成窗口，然后再拼接窗口级样本；或者在拼接数据中保留 `source_file / experiment_id / segment_id`，生成窗口时丢弃跨文件边界的窗口。

## 7. 窗口大小选择

JumpStarter 的核心输入是滑动窗口。当前数据采样间隔为：

```text
30 秒 / 点
```

前期尝试过较长窗口，但由于本实验的故障持续时间较短，20 分钟窗口不适合当前数据规模。当前推荐：

```text
window_size = 10 点 = 5 分钟
```

对应配置文件：

```text
mydata/processed/signal_log_based/configs/test_all_signal_w10.yml
```

注意：这里的 `w10` 表示 10 个采样点，不是 10 分钟。

## 8. 当前实验结果

推荐配置：

```text
mydata/processed/signal_log_based/configs/test_all_signal_w10.yml
```

运行结果：

| 数据集 | 窗口 | Precision | Recall | F1 |
| --- | ---: | ---: | ---: | ---: |
| `test_all_signal_w10` | 5 分钟 | 61.65 | 95.35 | 74.89 |
| `test_no_delay_signal_w10` | 5 分钟 | 50.00 | 92.31 | 64.86 |

结论：

1. 保留 `fault_delay_cart_repeat_500ms.csv` 后效果更好；
2. 5 分钟窗口明显优于 10-20 分钟窗口；
3. 当前结果适合作为 Online Boutique 场景下的 JumpStarter 复现实验结果；
4. 由于训练数据量仍然较小，该结果更适合作为课程/实验复现，不代表生产环境可用精度。

说明：表中 `test_all_signal_w10` 采用重构 observed-impact 打标版本之前的 log-based 历史主结果；当前目录已重构为 `mydata/processed/signal_log_based/`，但数据组成和标签语义保持对应。

## 9. 运行方式

推荐运行方式统一记录在：

```text
docs/REPRODUCTION-OVERVIEW.md#7-run-detector
```

输出文件会写入：

```text
mydata/processed/signal_log_based/result/
```

主要输出包括：

```text
test_all_signal_w10_score.txt
test_all_signal_w10_rec.txt
```

## 10. 目录说明

```text
JumpStarter/
|-- detector/
|   |-- run_detector.py
|   |-- cs_anomaly_detector.py
|   `-- detector-config.yml
|-- mydata/
|   |-- raw_self/
|   |   |-- normal_train.csv
|   |   |-- normal_valid.csv
|   |   |-- fault_cpu_frontend.csv
|   |   |-- fault_mem_recommendation.csv
|   |   |-- fault_delay_cart_repeat_500ms.csv
|   |   `-- fault_kill_product_repeat.csv
|   |-- scripts/
|   |   |-- process_mydata.py
|   |   |-- make_signal_dataset.py
|   |   `-- make_observed_signal_dataset.py
|   |-- processed/
|   |   |-- full_log_based/
|   |   |-- signal_log_based/
|   |   `-- signal_observed/
|   |-- external/
|   |   |-- ll_data/
|   |   |-- ll_data_new/
|   |   `-- partner_hyx_data/
|   |-- experiment-log.md
|   `-- README.md
|-- docs/
|   |-- GDN/
|   `-- JumpStarter/
`-- README.md
```

## 11. 局限与后续工作

当前主要限制：

1. 正常训练数据仍然偏少；
2. 故障类型数量有限；
3. 当前检测是离线批处理，不是实时流式检测；
4. JumpStarter 输出主要是异常分数，不直接给出精确根因服务；
5. 后续若要服务运维 agent，需要增加结果汇总文件和时间戳映射。

建议后续优化：

1. 将正常训练数据扩展到 2-4 小时；
2. 每类故障重复采集多轮；
3. 将 score 输出转换为 CSV，保留真实时间戳；
4. 增加 top anomalous metrics 的辅助定位逻辑；
5. 封装一个统一 CLI 或文件接口给运维 agent 调用。
