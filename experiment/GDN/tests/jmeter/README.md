# 阶段三：JMeter 性能测试

## 测试计划

测试脚本：

```text
experiment/tests/jmeter/online-boutique-load.jmx
```

该脚本模拟 Online Boutique 常见用户行为：

1. 访问首页 `/`
2. 访问商品详情页 `/product/${PRODUCT_ID}`
3. 提交加购请求 `POST /cart`
4. 查看购物车 `/cart`
5. 提交结算请求 `POST /cart/checkout`

默认参数：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | `127.0.0.1` | frontend 主机 |
| `PORT` | `46921` | frontend 端口，按实际修改 |
| `THREADS` | `30` | 并发用户数 |
| `RAMP_UP` | `30` | 启动时间，秒 |
| `DURATION` | `600` | 持续时间，秒 |
| `PRODUCT_ID` | `OLJCESPC7Z` | 商品 ID |

## GUI 验证

```powershell
cd D:\tools\apache-jmeter-5.6.3\bin
.\jmeter.bat
```

打开：

```text
D:\soft\AndroidStudioProjects\Online-Boutique\experiment\tests\jmeter\online-boutique-load.jmx
```

先运行 1 分钟确认 `Error %` 为 0 或接近 0。

## 命令行正式运行

```powershell
cd D:\tools\apache-jmeter-5.6.3\bin

.\jmeter.bat -n `
  -t "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\tests\jmeter\online-boutique-load.jmx" `
  -l "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\results\jmeter\results.jtl" `
  -e -o "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\results\jmeter\html-report"
```

若 frontend 端口变化，可在命令行覆盖变量：

```powershell
.\jmeter.bat -n `
  -t "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\tests\jmeter\online-boutique-load.jmx" `
  -JPORT=46921 `
  -l "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\results\jmeter\results.jtl" `
  -e -o "D:\soft\AndroidStudioProjects\Online-Boutique\experiment\results\jmeter\html-report"
```

## 报告记录

打开：

```text
experiment/results/jmeter/html-report/index.html
```

记录以下指标：

- `# Samples`
- `Average`
- `Min / Max`
- `90% Line / 95% Line`
- `Throughput`
- `Error %`

