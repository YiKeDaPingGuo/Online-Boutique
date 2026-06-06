#!/usr/bin/env python3
"""Online Boutique checkout flow test for experiment phase 3."""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

import pytest
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.firefox.service import Service as FirefoxService
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

BASE_URL = os.getenv("BOUTIQUE_URL", "http://127.0.0.1:46921").rstrip("/")
BROWSER = os.getenv("BROWSER", "firefox").lower()
WAIT_TIMEOUT = int(os.getenv("SELENIUM_TIMEOUT", "20"))
RESULTS_DIR = Path(__file__).resolve().parents[2] / "results" / "selenium"
DRIVER_SETUP_HINT = (
    "Driver setup failed. Try one of:\n"
    "  1) $env:BROWSER='firefox'; python -m pytest ...\n"
    "  2) $env:WEBDRIVER_PATH='C:\\path\\to\\geckodriver.exe'\n"
    "  3) pip install webdriver-manager (needs network once)\n"
    "  4) Install geckodriver manually and add it to PATH"
)


def _resolve_driver_path(browser: str) -> str | None:
    generic = os.getenv("WEBDRIVER_PATH")
    if generic and Path(generic).is_file():
        return generic
    env_name = "GECKODRIVER_PATH" if browser == "firefox" else "CHROMEDRIVER_PATH"
    specific = os.getenv(env_name)
    if specific and Path(specific).is_file():
        return specific
    return None


def _service_from_manager(browser: str):
    try:
        if browser == "firefox":
            from webdriver_manager.firefox import GeckoDriverManager

            return FirefoxService(GeckoDriverManager().install())
        from webdriver_manager.chrome import ChromeDriverManager

        return ChromeService(ChromeDriverManager().install())
    except Exception:
        return None


def create_webdriver(browser: str | None = None):
    browser = (browser or BROWSER).lower()
    driver_path = _resolve_driver_path(browser)

    if browser == "firefox":
        options = FirefoxOptions()
        if driver_path:
            return webdriver.Firefox(service=FirefoxService(driver_path), options=options)
        service = _service_from_manager("firefox")
        if service:
            return webdriver.Firefox(service=service, options=options)
        try:
            return webdriver.Firefox(options=options)
        except WebDriverException as exc:
            raise WebDriverException(f"{exc}\n{DRIVER_SETUP_HINT}") from exc

    options = ChromeOptions()
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    if driver_path:
        return webdriver.Chrome(service=ChromeService(driver_path), options=options)
    service = _service_from_manager("chrome")
    if service:
        return webdriver.Chrome(service=service, options=options)
    try:
        return webdriver.Chrome(options=options)
    except WebDriverException as exc:
        raise WebDriverException(f"{exc}\n{DRIVER_SETUP_HINT}") from exc


@dataclass
class StepTiming:
    step: str
    elapsed_ms: float


class CheckoutFlowTest:
    def setup_method(self, method):
        self.driver = self._create_driver()
        self.driver.set_window_size(1440, 900)
        self.wait = WebDriverWait(self.driver, WAIT_TIMEOUT)
        self.timings: list[StepTiming] = []

    def teardown_method(self, method):
        if hasattr(self, "driver"):
            self.driver.quit()

    def _create_driver(self):
        return create_webdriver(BROWSER)

    def _run_step(self, name: str, action):
        start = time.perf_counter()
        action()
        elapsed_ms = (time.perf_counter() - start) * 1000
        self.timings.append(StepTiming(name, round(elapsed_ms, 2)))

    def _save_timings(self):
        RESULTS_DIR.mkdir(parents=True, exist_ok=True)
        payload = {
            "base_url": BASE_URL,
            "browser": BROWSER,
            "finished_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "steps": [asdict(item) for item in self.timings],
            "total_ms": round(sum(item.elapsed_ms for item in self.timings), 2),
        }
        out_path = RESULTS_DIR / "checkout_flow_timings.json"
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"Saved step timings to {out_path}")

    def test_checkout_flow(self):
        self._run_step("open_homepage", lambda: self._open_homepage())
        self._run_step("open_product", lambda: self._open_first_product())
        self._run_step("add_to_cart", lambda: self._add_product_to_cart(quantity="3"))
        self._run_step("place_order", lambda: self._place_order())
        self._run_step("continue_shopping", lambda: self._continue_shopping())

        total_ms = sum(item.elapsed_ms for item in self.timings)
        print("Selenium checkout flow passed.")
        for item in self.timings:
            print(f"  - {item.step}: {item.elapsed_ms} ms")
        print(f"  - total: {total_ms:.2f} ms")
        self._save_timings()

    def _open_homepage(self):
        self.driver.get(f"{BASE_URL}/")
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".hot-products-row h3")))
        assert "Hot Products" in self.driver.page_source

    def _open_first_product(self):
        product_link = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, ".hot-product-card a"))
        )
        product_link.click()
        self.wait.until(EC.presence_of_element_located((By.ID, "quantity")))
        assert "/product/" in self.driver.current_url

    def _add_product_to_cart(self, quantity: str = "3"):
        Select(self.wait.until(EC.presence_of_element_located((By.ID, "quantity")))).select_by_visible_text(
            quantity
        )
        add_button = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Add To Cart']"))
        )
        add_button.click()
        self.wait.until(EC.url_contains("/cart"))
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".cart-summary-item-row")))
        self.wait.until(EC.text_to_be_present_in_element((By.TAG_NAME, "body"), f"Quantity: {quantity}"))

    def _place_order(self):
        email = self.wait.until(EC.presence_of_element_located((By.ID, "email")))
        email.clear()
        email.send_keys("gdn-test@example.com")

        street = self.driver.find_element(By.ID, "street_address")
        street.clear()
        street.send_keys("123 Test Street")

        place_order = self.wait.until(
            EC.element_to_be_clickable((By.XPATH, "//button[normalize-space()='Place Order']"))
        )
        place_order.click()
        self.wait.until(
            EC.text_to_be_present_in_element(
                (By.TAG_NAME, "body"),
                "Your order is complete!",
            )
        )
        assert "Your order is complete!" in self.driver.page_source

    def _continue_shopping(self):
        continue_link = self.wait.until(
            EC.element_to_be_clickable((By.LINK_TEXT, "Continue Shopping"))
        )
        continue_link.click()
        self.wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, ".hot-products-row h3")))
        assert self.driver.current_url.rstrip("/") in {BASE_URL, f"{BASE_URL}/"}


# pytest discovers Test* classes; keep alias for IDE exports.
class TestCheckoutFlow(CheckoutFlowTest):
    pass


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-v"]))
