# processed Online Boutique dataset

这个目录由 `../process_mydata.py` 生成，用于把 `mydata` 原始 CSV 转成 JumpStarter 输入格式。

## 内容

- `data/`：去掉 `timestamp` 和 header 后的纯数值 CSV。
- `label/`：和 `data/` 同行数的 0/1 label。
- `configs/`：可直接传给 `detector/run_detector.py` 的配置。
- `metadata/summary.csv`：每个文件的行数、列数、时间范围、正样本数量。
- `metadata/feature_columns.txt`：进入模型的 55 个指标列。
- `result/`：JumpStarter 运行结果目录。

## Label 规则

- normal 文件全部标为 0。
- CPU / memory stress 使用故障开始到故障结束时间段标为 1。
- repeated network delay 使用日志中建议的扩展异常段。
- repeated pod kill 使用每次 kill 后 2 分钟恢复窗口。

## 运行

从项目根目录重新处理：

```powershell
python mydata\process_mydata.py
```

从 `detector/` 目录运行合并测试集：

```powershell
$env:PYTHONNOUSERSITE='1'
conda run -n jumpstarter python run_detector.py -c ..\mydata\processed\configs\test_all.yml
```
