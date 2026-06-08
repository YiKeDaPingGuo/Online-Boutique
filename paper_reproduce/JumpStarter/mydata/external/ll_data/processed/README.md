# ll_data processed dataset

这个目录由 `../process_ll_data.py` 生成，用于把 `ll_data` 原始 CSV 转成 JumpStarter 的输入格式。

## 目录结构

- `data/`：去掉 `timestamp` 和 header 后的纯数值 CSV。
- `label/`：和 `data/` 同行数的 0/1 标签 CSV。
- `configs/`：可以直接传给 `detector/run_detector.py` 的小窗口配置。
- `metadata/summary.csv`：每个文件的处理摘要、时间范围和正样本数量。
- `metadata/kept_columns.txt`：保留的指标列。
- `metadata/dropped_all_empty_columns.txt`：因为全为空而丢弃的列。
- `result/`：JumpStarter 运行后的重建结果和 anomaly score。

## 处理规则

原始 CSV 的 `timestamp` 只用于生成 label，不进入模型输入。

`net_rx` / `net_tx` 列在这批旧数据中为空，因此处理时被丢弃。最终保留 22 个指标列，即 11 个服务的 `cpu` 和 `mem`。

故障文件的 label 根据 `experiment-log.md` 中的故障开始和结束时间生成：

- 正常时间点：0
- 故障注入到故障结束：1

`test_all.csv` 是 `normal_valid + fault_cpu_frontend + fault_delay_cart + fault_kill_product` 的合并测试集。

## 运行命令

在项目根目录重新生成处理数据：

```powershell
python mydata\external\ll_data\process_ll_data.py
```

在 `jumpstarter` conda 环境中运行合并测试集：

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\external\ll_data\processed\configs\test_all.yml
```

运行目录需要是：

```text
detector/
```
