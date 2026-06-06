# 阶段三：Selenium 功能测试

## 测试内容

脚本 `test_checkout_flow.py` 覆盖 Online Boutique 完整购物流程：

1. 打开首页
2. 进入商品详情页
3. 选择数量并加入购物车
4. 填写结算信息并下单
5. 验证订单成功页
6. 返回继续购物

运行后会输出每步耗时，并保存到：

```text
experiment/results/selenium/checkout_flow_timings.json
```

## 环境准备

```powershell
pip install -r experiment/tests/selenium/requirements.txt
```

确保 frontend 可访问。若使用 Minikube：

```powershell
minikube service frontend -n onlineboutique --url
```

记下 URL，例如 `http://127.0.0.1:46921`。

## 运行方式

```powershell
cd D:\soft\AndroidStudioProjects\Online-Boutique
pip install -r experiment/tests/selenium/requirements.txt

# 默认 Firefox（与 Selenium IDE 录制环境一致）
$env:BOUTIQUE_URL = "http://127.0.0.1:46921"
python -m pytest experiment/tests/selenium/test_checkout_flow.py -v
```

可选环境变量：

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `BOUTIQUE_URL` | `http://127.0.0.1:46921` | frontend 地址 |
| `BROWSER` | `firefox` | 可选 `firefox` / `chrome` |
| `WEBDRIVER_PATH` | 空 | 手动指定 geckodriver/chromedriver 路径 |
| `GECKODRIVER_PATH` | 空 | Firefox 驱动路径 |
| `CHROMEDRIVER_PATH` | 空 | Chrome 驱动路径 |
| `SELENIUM_TIMEOUT` | `20` | 显式等待秒数 |

## 驱动报错排查

若出现 `Unable to obtain driver for chrome`，通常是 Selenium Manager 无法联网下载驱动。

**推荐方案（Firefox）：**

```powershell
$env:BROWSER = "firefox"
python -m pytest experiment/tests/selenium/test_checkout_flow.py -v
```

**手动指定驱动：**

```powershell
$env:BROWSER = "firefox"
$env:WEBDRIVER_PATH = "C:\path\to\geckodriver.exe"
python -m pytest experiment/tests/selenium/test_checkout_flow.py -v
```

**使用 webdriver-manager 自动下载（需可访问外网一次）：**

```powershell
pip install webdriver-manager
python -m pytest experiment/tests/selenium/test_checkout_flow.py -v
```

## 报告建议

在实验报告中记录：

- 测试是否通过（订单成功页断言）
- 各步骤耗时（来自 JSON 或控制台输出）
- 浏览器类型
- 说明 loadgenerator 为后台持续流量，Selenium 为显式端到端功能验证
