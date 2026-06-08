"""
手动性能测量辅助脚本（基于 Selenium）
自动记录页面加载时间、交互响应时间，并截取关键页面截图

输出：
  - screenshots/ 目录：各页面截图
  - performance_report_时间戳.csv：结构化性能数据
"""

import time
import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# ====== 配置区 ======
BASE_URL = "http://localhost:8081"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "manual_test_output")
SCREENSHOT_DIR = os.path.join(OUTPUT_DIR, "screenshots")
CSV_PATH = os.path.join(OUTPUT_DIR, f"performance_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")

# 创建输出目录
os.makedirs(SCREENSHOT_DIR, exist_ok=True)

# ====== 初始化浏览器 ======
options = Options()
# options.add_argument("--headless=new")  # 取消注释以使用无头模式
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")
service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
wait = WebDriverWait(driver, 10)

# 用于存储测量结果
results = []


def measure_page_load(url, name, screenshot=True):
    """测量页面加载时间并截图"""
    print(f"\n{'='*50}")
    print(f"[测量] {name}")
    print(f"[URL]  {url}")

    # 记录开始时间
    start_time = time.time()

    # 加载页面
    driver.get(url)

    # 等待页面完全加载
    wait.until(lambda d: d.execute_script("return document.readyState") == "complete")
    load_time = time.time() - start_time

    # 使用 Performance API 获取更详细的指标
    perf = driver.execute_script("""
        const perf = performance.timing;
        const nav = performance.getEntriesByType('navigation')[0];
        return {
            domContentLoaded: perf.domContentLoadedEventEnd - perf.navigationStart,
            domInteractive: perf.domInteractive - perf.navigationStart,
            domComplete: perf.domComplete - perf.navigationStart,
            firstByte: perf.responseStart - perf.navigationStart,
            totalLoadTime: perf.loadEventEnd - perf.navigationStart,
            // 较新的指标（Navigation API Level 2）
            fetchStart: nav ? nav.fetchStart : 0,
            responseEnd: nav ? nav.responseEnd : 0
        };
    """)

    print(f"  [总加载时间] {load_time:.2f}s")
    print(f"  [首字节]     {perf['firstByte']}ms")
    print(f"  [DOM 解析]   {perf['domContentLoaded']}ms")
    print(f"  [DOM 完成]   {perf['domComplete']}ms")

    # 记录结果
    results.append({
        "页面": name,
        "总加载时间(s)": round(load_time, 3),
        "首字节(ms)": perf['firstByte'],
        "DOM解析(ms)": perf['domContentLoaded'],
        "DOM完成(ms)": perf['domComplete'],
    })

    # 截图
    if screenshot:
        filename = name.replace("/", "_").replace(" ", "_") + ".png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        driver.save_screenshot(filepath)
        print(f"  [截图保存]   {filepath}")

    return load_time


def measure_interaction(description, action_func, screenshot=True):
    """测量交互操作的响应时间"""
    print(f"\n  [交互] {description}")
    start_time = time.time()
    action_func()
    elapsed = time.time() - start_time
    print(f"  [响应时间] {elapsed:.2f}s")

    if screenshot:
        filename = description.replace("/", "_").replace(" ", "_") + ".png"
        filepath = os.path.join(SCREENSHOT_DIR, filename)
        driver.save_screenshot(filepath)
        print(f"  [截图保存]   {filepath}")

    # 记录结果
    results.append({
        "页面": description,
        "总加载时间(s)": round(elapsed, 3),
        "首字节(ms)": "",
        "DOM解析(ms)": "",
        "DOM完成(ms)": "",
    })
    return elapsed


def save_report():
    """保存 CSV 报告"""
    with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["页面", "总加载时间(s)", "首字节(ms)", "DOM解析(ms)", "DOM完成(ms)"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\n{'='*50}")
    print(f"[报告保存] {CSV_PATH}")


def print_summary():
    """打印汇总"""
    print(f"\n{'='*50}")
    print("测试汇总")
    print(f"{'='*50}")
    for r in results:
        print(f"  {r['页面']:30s}  {r['总加载时间(s)']:>6.2f}s")


# ====== 开始测试 ======
try:
    print("=" * 50)
    print("Online Boutique 手动性能测量")
    print("开始时间:", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 50)

    # 1. 首页加载
    measure_page_load(BASE_URL + "/", "首页", screenshot=True)

    # 2. 商品详情页
    measure_page_load(BASE_URL + "/product/OLJCESPC7Z", "商品详情-Sunglasses", screenshot=True)

    # 3. 空购物车页
    measure_page_load(BASE_URL + "/cart", "空购物车", screenshot=True)

    # 4. 添加商品到购物车（含交互时间）
    def add_to_cart():
        driver.get(BASE_URL + "/product/OLJCESPC7Z")
        wait.until(EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add To Cart')]"))).click()

    measure_interaction("添加商品到购物车", add_to_cart, screenshot=True)

    # 5. 结算页面（含填写信息）
    def checkout_flow():
        # 填写并提交结算表单
        email = driver.find_element(By.ID, "email")
        email.clear()
        email.send_keys("test@university.edu")

        street = driver.find_element(By.ID, "street_address")
        street.clear()
        street.send_keys("100 University Ave")

        zip_code = driver.find_element(By.ID, "zip_code")
        zip_code.clear()
        zip_code.send_keys("10001")

        city = driver.find_element(By.ID, "city")
        city.clear()
        city.send_keys("New York")

        state = driver.find_element(By.ID, "state")
        state.clear()
        state.send_keys("NY")

        country = driver.find_element(By.ID, "country")
        country.clear()
        country.send_keys("USA")

        cc_number = driver.find_element(By.ID, "credit_card_number")
        cc_number.clear()
        cc_number.send_keys("4432801561520454")

        cc_cvv = driver.find_element(By.ID, "credit_card_cvv")
        cc_cvv.clear()
        cc_cvv.send_keys("672")

        month_select = Select(driver.find_element(By.ID, "credit_card_expiration_month"))
        month_select.select_by_value("12")

        # 提交订单
        driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]").click()

    measure_interaction("结算下单流程", checkout_flow, screenshot=True)

    # 6. 切换货币
    def switch_currency():
        driver.get(BASE_URL)
        select = Select(driver.find_element(By.NAME, "currency_code"))
        select.select_by_value("EUR")
        driver.find_element(By.ID, "currency_form").submit()
        wait.until(EC.presence_of_element_located((By.CLASS_NAME, "hot-product-card")))

    measure_interaction("切换货币(EUR)", switch_currency, screenshot=True)

    # 汇总
    print_summary()
    save_report()

finally:
    driver.quit()
    print("\n测试完成，浏览器已关闭。")
