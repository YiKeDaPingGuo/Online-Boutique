# JumpStarter mydata tuning report

## 已生成的数据版本

- `processed/`：原始 55 指标版本，包含全部故障。
- `processed/no_delay_legacy/`：去掉 `fault_delay_cart_repeat_500ms.csv` 的对照版本。
- `processed/signal_log_based/`：去掉所有 `_latency` 列，保留 `cpu/mem/request_rate/error_rate` 的 44 指标版本。

## 关键结论

1. 去掉 delay_cart 后没有改善，F1 反而下降。
2. `fault_delay_cart_repeat_500ms.csv` 不是低 precision 的主要原因，保留它更合适。
3. 5 分钟窗口明显优于之前的 10 分钟/20 分钟窗口，更适合当前 30 秒采样、短故障持续时间的数据。
4. 当前 JumpStarter 原评价函数会从阈值 0 开始搜索，很多 score 为 0 时容易退化成“全判异常”；5 分钟窗口后这个问题显著缓解。
5. 对这批 Online Boutique 数据，部分长窗口结果呈现“低分更像异常”的现象；5 分钟窗口下原项目默认的“高分异常”方向更合理。
6. 单故障里 network delay 最容易被当前配置捕捉，memory 次之，CPU 和 pod kill 较弱。

## 主要结果

| 数据版本 | 原始评价 F1 | 低分异常 F1 | 说明 |
|---|---:|---:|---|
| processed/test_all | 33.99 | 40.38 | 55 指标，全部故障 |
| processed/signal_log_based/test_all_signal | 33.99 | 44.38 | 44 指标，去掉 latency，全部故障 |
| processed/signal_log_based/test_no_delay_signal | 26.53 | 39.39 | 去掉 delay 后更差 |
| processed/signal_log_based/test_all_signal_w10 | 65.90 | - | 5 分钟窗口，全部故障，原项目段级评价 |
| processed/signal_log_based/test_no_delay_signal_w10 | 64.86 | - | 5 分钟窗口，去掉 delay，原项目段级评价 |
| processed/signal_log_based/test_cpu_frontend_signal | 22.22 | 31.75 | CPU 单故障较弱 |
| processed/signal_log_based/test_mem_recommendation_signal | 22.22 | 42.50 | memory 单故障较好 |
| processed/signal_log_based/test_delay_cart_repeat_500ms_signal | 39.08 | 47.89 | delay 单故障最好 |
| processed/signal_log_based/test_kill_product_repeat_signal | 15.79 | 24.49 | pod kill 单故障最弱 |

完整离线分析结果见：

```text
mydata/score_analysis.csv
```

## 推荐下一步

当前更推荐继续使用：

```text
mydata/processed/signal_log_based/data/test_all_signal.csv
mydata/processed/signal_log_based/label/test_all_signal.csv
mydata/processed/signal_log_based/configs/test_all_signal_w10.yml
```

运行命令：

```powershell
cd detector
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_all_signal.yml
```

5 分钟窗口推荐命令：

```powershell
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\signal_log_based\configs\test_all_signal_w10.yml
```

如果要报告当前结果，建议优先报告 5 分钟窗口版本，并说明：

> 在 Online Boutique 数据上，故障持续时间较短且采样间隔为 30 秒，使用 5 分钟窗口比 10-20 分钟窗口更适合当前数据规模和异常持续时间。5 分钟窗口下，JumpStarter 在包含全部故障的测试集上取得 Precision 49.14%、Recall 100.00%、F1 65.90%。
