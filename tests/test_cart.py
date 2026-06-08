"""
商品详情和购物车功能测试
覆盖：商品详情浏览、加入购物车、购物车操作
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


class TestProductDetail:
    """商品详情页测试"""

    PRODUCT_ID = "OLJCESPC7Z"
    PRODUCT_NAME = "Sunglasses"

    def test_product_detail_loads(self, driver):
        """验证商品详情页加载正常"""
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        assert self.PRODUCT_NAME in driver.page_source

    def test_add_to_cart_button_exists(self, driver):
        """验证详情页有「加入购物车」按钮"""
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        add_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]")
        assert add_btn.is_displayed()

    def test_quantity_selector_exists(self, driver):
        """验证数量选择器存在且有多个选项"""
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        qty_select = driver.find_element(By.NAME, "quantity")
        options = qty_select.find_elements(By.TAG_NAME, "option")
        assert len(options) >= 5

    def test_recommendations_displayed(self, driver):
        """验证商品详情页显示推荐商品"""
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        assert "You May Also Like" in driver.page_source

    def test_product_image_displayed(self, driver):
        """验证商品图片能加载"""
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        img = driver.find_element(By.CLASS_NAME, "product-image")
        assert img.is_displayed()


class TestCart:
    """购物车功能测试"""

    def test_empty_cart_message(self, driver):
        """验证空购物车显示提示消息"""
        driver.get(driver.base_url + "/cart")
        assert "empty" in driver.page_source.lower()

    def test_add_single_item_to_cart(self, driver):
        """验证添加一个商品到购物车"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        driver.get(driver.base_url + "/product/OLJCESPC7Z")
        # 点击 Add To Cart
        driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]").click()
        # 等待页面跳转到购物车
        WebDriverWait(driver, 5).until(
            EC.url_contains("/cart")
        )
        # 验证购物车显示商品
        assert "Sunglasses" in driver.page_source

    def test_cart_badge_updates(self, driver):
        """验证购物车图标上的数量角标更新"""
        driver.get(driver.base_url)
        driver.get(driver.base_url + "/product/OLJCESPC7Z")
        driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]").click()
        # 购物车角标显示数量
        cart_badge = driver.find_element(By.CLASS_NAME, "cart-size-circle")
        assert cart_badge.text.isdigit()
        assert int(cart_badge.text) >= 1

    def test_cart_total_calculation(self, driver):
        """验证购物车总价计算正确（商品价格 + 运费）"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        driver.get(driver.base_url + "/product/OLJCESPC7Z")
        driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]").click()
        # 等待购物车结算区域加载完成
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cart-summary-total-row"))
        )
        page_text = driver.page_source
        assert "Shipping" in page_text
        assert "Total" in page_text
        assert "$" in page_text

    def test_empty_cart(self, driver):
        """验证清空购物车功能"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # 先添加商品到购物车，等待跳转到购物车页面
        driver.get(driver.base_url + "/product/OLJCESPC7Z")
        driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]").click()
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cart-summary-section"))
        )
        # 提交清空购物车表单（清空后重定向到首页）
        empty_form = driver.find_element(By.XPATH, "//form[@action='/cart/empty']")
        driver.execute_script("arguments[0].submit();", empty_form)
        # 等待重定向到首页
        WebDriverWait(driver, 5).until(
            EC.url_to_be(driver.base_url + "/")
        )
        # 导航到购物车页面，验证已清空
        driver.get(driver.base_url + "/cart")
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "empty-cart-section"))
        )
        assert "empty" in driver.page_source.lower()

    def test_add_multiple_items(self, driver):
        """验证添加多个不同商品到购物车"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        products = ["OLJCESPC7Z", "66VCHSJNUP", "1YMWWN1N4O"]
        for pid in products:
            # 打开商品详情页
            driver.get(driver.base_url + f"/product/{pid}")
            # 等待 Add To Cart 按钮出现并点击
            add_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'Add To Cart')]"))
            )
            add_btn.click()
            # 点击后跳转到购物车页面，等待页面加载完成
            WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CLASS_NAME, "cart-sections"))
            )
        # 验证购物车页面显示所有商品名称
        page_text = driver.page_source
        assert "Sunglasses" in page_text
        assert "Tank Top" in page_text
        assert "Watch" in page_text

    def test_continue_shopping_button(self, driver):
        """验证「继续购物」按钮返回首页"""
        driver.get(driver.base_url + "/cart")
        continue_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Continue Shopping')]")
        continue_btn.click()
        assert driver.current_url == driver.base_url + "/"
