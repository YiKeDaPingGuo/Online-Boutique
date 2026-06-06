# Online Boutique + GDN 实验报告模板

---

## 1. 实验概述

### 1.1 实验目标

本实验在 Online Boutique 微服务系统上复现 GDN（Graph Deviation Network）异常检测方法，验证其在 Kubernetes 监控场景下对 CPU 压力、网络延迟、Pod Kill 三类故障的检测能力。

### 1.2 论文信息

- 论文：Graph Neural Network-Based Anomaly Detection in Multivariate Time Series
- 作者：Ailin Deng, Bryan Hooi
- 核心思想：学习传感器/指标间依赖图，通过预测偏差检测异常

### 1.3 实验环境

| 项目 | 配置 |
|------|------|
| 操作系统 | Windows 10 |
| 容器编排 | Minikube + Kubernetes |
| 微服务系统 | Online Boutique（namespace: `onlineboutique`） |
| 监控 | Prometheus + Grafana 7.5 |
| 故障注入 | ChaosMesh（namespace: `chaos-testing`） |
| 算法实现 | `experiment/scripts/run_gdn_reproduction.py`|

---

## 2. 阶段一：微服务部署

### 2.1 部署步骤

1. 启动 Minikube
2. 部署 Online Boutique：`kubectl apply -f release/kubernetes-manifests.yaml`
3. 验证 Pod / Service 状态

### 2.2 部署结果

- 运行服务数：Online Boutique 11 个核心微服务 + `loadgenerator`
- 访问方式：通过 Minikube 暴露 `frontend`
- 是否正常：系统可正常访问首页、商品详情页、购物车与结算流程

---

## 3. 阶段二：监控与数据采集

### 3.1 Prometheus + Grafana

- Prometheus 地址：`自己的地址`
- Grafana Dashboard：`grafana/dashboard-online-boutique-gdn-v7.json`
- 采集指标：CPU、内存（当前集群无 pod 级网络指标）

### 3.2 正常数据

| 数据集 | 时间范围 | 行数 | 文件 |
|--------|----------|------|------|
| 训练集 | 2026-06-05 12:36:43 → 2026-06-05 13:06:43 | 61 | `data/normal_train.csv` |
| 验证集 | 2026-06-05 12:56:43 → 2026-06-05 13:06:43 | 21 | `data/normal_valid.csv` |

### 3.3 故障注入实验

| 实验 | 故障类型 | 目标服务 | 注入时间 | 结束时间 | 数据文件 |
|------|----------|----------|----------|----------|----------|
| 实验 3 | CPU Stress | frontend | 2026-06-06 18:22:56 | 2026-06-06 18:27:57 | `fault_cpu_frontend.csv` |
| 实验 4 | Network Delay | cartservice | 2026-06-06 18:37:40 | 2026-06-06 18:42:41 | `fault_delay_cart.csv` |
| 实验 5 | Pod Kill | productcatalogservice | 2026-06-06 19:23:41 | 2026-06-06 19:28:42 | `fault_kill_product.csv` |

### 3.4 标签定义

attack=1 的时间窗口 = 故障注入开始 → 故障结束 + **2 分钟恢复期**。

---

## 4. 阶段三：JMeter / Selenium 测试

### 4.1 JMeter 性能测试

- 测试目标：`Online-Boutique frontend`
- 并发用户数：30
- Ramp-Up：30 秒
- 持续时间：10 分钟
- 测试路径：`/` → `/product/OLJCESPC7Z` → `POST /cart` → `/cart` → `POST /cart/checkout`
- 测试计划：`experiment/tests/jmeter/online-boutique-load.jmx`
- HTML 报告：`experiment/results/html-report/index.html`

**结果摘要：**

| 指标 | 结果 |
|------|------|
| 总请求数 | 17041 |
| 平均响应时间 | 391.30 ms |
| 中位数响应时间 | 284.00 ms |
| 最小 / 最大响应时间 | 3.00 ms / 2307.00 ms |
| 90% / 95% / 99% 响应时间 | 931.00 ms / 1147.00 ms / 1500.16 ms |
| 吞吐量 | 28.41 requests/s |
| 错误数 | 0 |
| 错误率 | 0.00% |

各请求平均响应时间如下：

| 请求 | 样本数 | 平均响应时间 | 错误率 |
|------|--------|--------------|--------|
| `GET /` | 2448 | 602.64 ms | 0.00% |
| `GET /product/OLJCESPC7Z` | 2441 | 366.35 ms | 0.00% |
| `POST /cart` | 2433 | 514.09 ms | 0.00% |
| `GET /cart` | 2431 | 397.29 ms | 0.00% |
| `POST /cart/checkout` | 2422 | 343.38 ms | 0.00% |

### 4.2 Selenium 功能测试

- 浏览器：Firefox
- 测试流程：首页 → 浏览商品 → 加入购物车 → 结算
- 是否通过：通过（`1 passed`）
- 结果文件：`experiment/results/selenium/checkout_flow_timings.json`
- 页面交互总耗时：2562.12 ms

### 4.3 补充说明

loadgenerator 已持续产生流量，可作为 JMeter 的补充流量源。

Selenium 各步骤耗时如下：

| 步骤 | 耗时 |
|------|------|
| 打开首页 | 1059.39 ms |
| 打开商品详情页 | 382.04 ms |
| 加入购物车 | 320.57 ms |
| 提交订单 | 629.62 ms |
| 返回继续购物 | 170.50 ms |

---

## 5. 阶段四：GDN 算法复现

### 5.1 数据预处理

1. 使用 `export_metrics.py` 从 Prometheus 导出 CSV
2. 使用 `prepare_gdn_data.py` 转换为 GDN 格式
3. 自动剔除全空网络列，保留 22 个 cpu/mem 特征

### 5.2 模型配置

| 参数 | 值 |
|------|-----|
| 特征数 | 22 |
| 窗口大小 window | 5 |
| embedding 维度 | 64 |
| TopK | 15 |
| 训练 epoch | 120 |
| 阈值策略 | 验证集最大异常分数 |

### 5.3 实验结果

```text
precision: 0.8462
recall:    1.0000
f1:        0.9167
threshold: 24.683069
```

| 故障类型 | Precision | Recall | 说明 |
|----------|-----------|--------|------|
| CPU | 1.000 | 1.000 | 零误报 |
| 网络延迟 | 0.789 | 1.000 | 故障前缓冲段有 FP |
| Pod Kill | 0.789 | 1.000 | 故障前缓冲段有 FP |

### 5.4 与论文对比

| 数据集 | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| SWaT（论文） | 99.35% | 68.12% | 0.81 |
| WADI（论文） | 97.50% | 40.19% | 0.57 |
| Online Boutique（本实验） | 84.62% | 100.00% | 0.92 |

### 5.5 异常定位（Top 特征）

1. `emailservice_mem`
2. `cartservice_mem`
3. `recommendationservice_mem`
4. `productcatalogservice_mem`
5. `paymentservice_mem`
6. `adservice_mem`
7. `frontend_cpu`
8. `emailservice_cpu`
9. `currencyservice_mem`
10. `frontend_mem`

---

## 6. 结果分析

### 6.1 是否达到预期

- 算法流程复现：基本达到。实验完成了 Sensor Embedding、TopK 图结构学习、图注意力预测、鲁棒偏差打分和阈值判定流程。
- 故障检测能力：达到预期。Recall=100%，CPU、网络延迟、Pod Kill 三类故障均被检出。
- 精度水平：Precision=84.62%，低于论文 SWaT/WADI 的 97%–99%，但考虑到本实验为微服务场景迁移、训练集较短、监控指标较少，该结果可作为有效复现结果。

### 6.2 主要问题

1. 训练集较短（30 分钟），少于论文数万条样本
2. 当前 Minikube 无 pod 级网络指标，无法使用 net_rx/net_tx
3. 当前仅完成单轮 JMeter 与 Selenium 测试，尚未做多并发梯度对比（如 10/30/50 用户）

### 6.3 优化措施与效果

| 优化措施 | 效果 |
|----------|------|
| 精确计时重采故障数据 | Precision 0.48 → 0.55 |
| 恢复期标签 + Pod Kill 5min | Precision 0.55 → **0.85** |
| 剔除无效网络特征 | 特征数 44 → 22，结果保持 Precision=0.8462，同时异常贡献特征更可信 |

---

## 7. 结论与展望

### 7.1 结论

本实验完成了 Online Boutique 微服务系统部署、Prometheus/Grafana 监控、ChaosMesh 故障注入、JMeter/Selenium 阶段三测试，以及 GDN 异常检测算法复现。实验结果表明，GDN 在本地微服务场景中能够有效检测 CPU 压力、网络延迟和 Pod Kill 三类异常，最终 Precision 为 0.8462，Recall 为 1.0000，F1 为 0.9167。虽然 Precision 低于论文原始工业数据集结果，但在训练数据规模较小、指标维度较少的场景迁移条件下，整体复现效果达到课程实验预期。

### 7.2 后续工作

1. 延长正常训练集至 2–4 小时
2. 扩展 JMeter 多组并发测试，例如 10 / 30 / 50 用户对比
3. 探索启用 cAdvisor pod 级网络指标或使用替代流量指标
4. 尝试官方 GDN / PyTorch Geometric 环境以进一步贴近论文实现

---

## 附录

### A. 关键命令

```powershell
# 端口转发 Prometheus
kubectl port-forward -n monitoring svc/prometheus 19090:9090

# 导出指标
cd D:\soft\AndroidStudioProjects\Online-Boutique\experiment
python scripts/export_metrics.py --probe-only
python scripts/prepare_gdn_data.py
python scripts/run_gdn_reproduction.py --epochs 120
```

### B. 文件清单

```text
experiment/
├── data/                    # CSV 原始数据
├── chaos/                   # ChaosMesh YAML
├── scripts/                 # 导出、预处理、GDN 脚本
├── results/                 # GDN 输出
├── experiment-log.md        # 实验时间记录
├── PHASE4-GDN.md            # 阶段四说明
└── EXPERIMENT-REPORT-TEMPLATE.md
```

### C. 参考文献

- GDN 论文（见 essay.md）
- GDN 官方仓库：https://github.com/d-ailin/GDN
