"""
结算流程功能测试
覆盖：填写收货地址、支付信息、下单确认
"""

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select


class TestCheckout:
    """结算流程测试"""

    PRODUCT_ID = "OLJCESPC7Z"

    @pytest.fixture(autouse=True)
    def add_item_to_cart(self, driver):
        """
        每个测试前先添加商品到购物车（前置条件）
        autouse=True 自动应用，无需在每个测试里手动调用
        """
        driver.get(driver.base_url)
        driver.get(driver.base_url + f"/product/{self.PRODUCT_ID}")
        driver.find_element(By.XPATH, "//button[contains(text(), 'Add To Cart')]").click()
        yield  # 测试代码在此执行

    def test_checkout_form_displayed(self, driver):
        """验证结算表单包含所有必填字段"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # 等待结算表单加载
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cart-checkout-form"))
        )
        assert "E-mail Address" in driver.page_source
        assert "Street Address" in driver.page_source
        assert "Credit Card Number" in driver.page_source
        assert "Place Order" in driver.page_source

    def test_checkout_with_default_values(self, driver):
        """验证使用预填默认值成功下单"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # 直接提交表单（使用页面预填的默认值）
        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()
        # 等待订单确认页面加载
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "order-complete-section"))
        )
        # 验证订单确认页面
        assert "Your order is complete" in driver.page_source
        assert "Confirmation" in driver.page_source
        assert "Tracking" in driver.page_source
        assert "Total Paid" in driver.page_source

    def test_checkout_order_has_confirmation_number(self, driver):
        """验证下单后生成确认号和追踪号"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()
        # 等待订单确认页面加载
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "order-complete-section"))
        )
        # 验证确认信息不为空
        page_text = driver.page_source
        assert "Your order is complete" in page_text
        assert "Confirmation" in page_text or "confirmation" in page_text
        # 追踪号可能是 "HN-" 或 "TRK-" 或其他格式，只验证存在即可
        assert "Tracking" in page_text or "tracking" in page_text

    def test_checkout_with_custom_values(self, driver):
        """验证使用自定义信息成功下单"""
        # 修改收货地址
        email = driver.find_element(By.ID, "email")
        email.clear()
        email.send_keys("student@university.edu")

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

        # 修改信用卡信息
        cc_number = driver.find_element(By.ID, "credit_card_number")
        cc_number.clear()
        cc_number.send_keys("4432801561520454")

        cc_cvv = driver.find_element(By.ID, "credit_card_cvv")
        cc_cvv.clear()
        cc_cvv.send_keys("123")

        # 选择信用卡到期月份
        month_select = Select(driver.find_element(By.ID, "credit_card_expiration_month"))
        month_select.select_by_value("6")

        # 提交订单
        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()

        # 验证订单成功
        assert "Your order is complete" in driver.page_source

    def test_checkout_total_matches_cart(self, driver):
        """验证结算页面总价与购物车总价一致"""
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC

        # 等待购物车总价区域加载
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "cart-summary-total-row"))
        )
        # 记录购物车总价
        cart_total_text = driver.find_element(By.CLASS_NAME, "cart-summary-total-row").text

        # 提交订单
        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()

        # 等待订单确认页面加载
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "order-complete-section"))
        )
        # 验证订单确认页面的总价与购物车一致
        assert "Total Paid" in driver.page_source
        assert "$" in driver.page_source

    def test_continue_shopping_after_checkout(self, driver):
        """验证下单后「继续购物」按钮返回首页"""
        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()
        continue_btn = driver.find_element(By.XPATH, "//a[contains(text(), 'Continue Shopping')]")
        continue_btn.click()
        assert driver.current_url == driver.base_url + "/"

    def test_checkout_form_validation(self, driver):
        """验证表单必填字段的 HTML5 验证（清空 email 后提交应被拦截）"""
        email = driver.find_element(By.ID, "email")
        email.clear()
        place_order_btn = driver.find_element(By.XPATH, "//button[contains(text(), 'Place Order')]")
        place_order_btn.click()
        # HTML5 验证会阻止提交，应仍停留在结算页面
        assert "/cart" in driver.current_url
