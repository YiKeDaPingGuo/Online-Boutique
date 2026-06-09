"""
pytest 配置文件：浏览器驱动管理和共享 fixture
使用 webdriver-manager 自动下载和管理 ChromeDriver
"""

import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager


# 应用访问地址（根据实际部署情况修改）
BASE_URL = "http://localhost:8081"


def pytest_addoption(parser):
    """添加命令行选项，支持无头模式切换"""
    parser.addoption(
        "--headless",
        action="store_true",
        default=True,
        help="以无头模式运行浏览器（默认开启）"
    )
    parser.addoption(
        "--base-url",
        action="store",
        default=BASE_URL,
        help=f"应用访问地址（默认 {BASE_URL}）"
    )


@pytest.fixture(scope="function")
def driver(request):
    """每个测试函数创建一个全新的 Chrome 浏览器实例"""
    headless = request.config.getoption("--headless")
    base_url = request.config.getoption("--base-url")

    chrome_options = Options()
    if headless:
        chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1280,800")
    # 禁用 GPU 加速（避免 Windows 下的兼容性问题）
    chrome_options.add_argument("--disable-gpu")

    # 自动管理 ChromeDriver 版本
    service = Service(ChromeDriverManager().install())
    browser = webdriver.Chrome(service=service, options=chrome_options)
    browser.implicitly_wait(5)  # 隐式等待最多 5 秒
    browser.base_url = base_url

    yield browser
    browser.quit()
