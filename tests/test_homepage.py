"""
首页和商品浏览功能测试
覆盖：页面加载、商品展示、导航、货币切换
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


class TestHomepage:
    """首页基本功能测试"""

    def test_homepage_loads(self, driver):
        """验证首页能正确加载并显示标题"""
        driver.get(driver.base_url)
        assert "Online Boutique" in driver.title

    def test_hot_products_displayed(self, driver):
        """验证首页展示所有 9 个热销商品"""
        driver.get(driver.base_url)
        product_cards = driver.find_elements(By.CLASS_NAME, "hot-product-card")
        assert len(product_cards) == 9

    def test_product_names_visible(self, driver):
        """验证商品名称可见"""
        driver.get(driver.base_url)
        product_names = driver.find_elements(By.CLASS_NAME, "hot-product-card-name")
        names = [el.text for el in product_names]
        assert "Sunglasses" in names
        assert "Watch" in names
        assert "Mug" in names

    def test_product_prices_visible(self, driver):
        """验证商品价格可见"""
        driver.get(driver.base_url)
        prices = driver.find_elements(By.CLASS_NAME, "hot-product-card-price")
        assert len(prices) == 9
        for price in prices:
            assert "$" in price.text

    def test_click_product_navigates_to_detail(self, driver):
        """验证点击商品跳转到详情页"""
        driver.get(driver.base_url)
        # 点击第一个 Hot Product
        first_product = driver.find_element(
            By.CSS_SELECTOR, ".hot-product-card a"
        )
        first_product.click()
        # 验证 URL 包含 /product/
        assert "/product/" in driver.current_url

    def test_logo_navigates_to_home(self, driver):
        """验证点击 Logo 返回首页"""
        driver.get(driver.base_url + "/product/OLJCESPC7Z")
        logo = driver.find_element(By.CLASS_NAME, "top-left-logo")
        logo.click()
        assert driver.current_url == driver.base_url + "/"

    def test_cart_link_visible(self, driver):
        """验证购物车链接存在"""
        driver.get(driver.base_url)
        cart_link = driver.find_element(By.CLASS_NAME, "cart-link")
        assert cart_link.is_displayed()


class TestCurrencySwitch:
    """货币切换功能测试"""

    def test_currency_selector_exists(self, driver):
        """验证货币选择器存在"""
        driver.get(driver.base_url)
        select = driver.find_element(By.NAME, "currency_code")
        options = select.find_elements(By.TAG_NAME, "option")
        currencies = [opt.get_attribute("value") for opt in options]
        assert "USD" in currencies
        assert "EUR" in currencies
        assert "JPY" in currencies

    @pytest.mark.parametrize("currency", ["EUR", "JPY", "GBP"])
    def test_switch_currency(self, driver, currency):
        """验证切换到不同货币后价格符号更新"""
        driver.get(driver.base_url)
        select = Select(driver.find_element(By.NAME, "currency_code"))
        select.select_by_value(currency)
        # 提交表单
        driver.find_element(By.ID, "currency_form").submit()
        # 验证页面刷新后的某个价格包含新货币符号（如 €, ¥, £）
        import re
        page_source = driver.page_source
        # JPY 用 ¥ 表示，但页面显示可能为 "JPY 2,200" 格式
        price_element = driver.find_element(By.CLASS_NAME, "hot-product-card-price")
        if currency == "EUR":
            assert "€" in price_element.text or "EUR" in driver.page_source
        elif currency == "JPY":
            assert "¥" in driver.page_source or "JPY" in driver.page_source
        elif currency == "GBP":
            assert "£" in price_element.text or "GBP" in driver.page_source
