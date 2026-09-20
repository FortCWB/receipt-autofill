from __future__ import annotations

import os
from typing import Iterable

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.common.by import By
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.edge.service import Service as EdgeService
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.microsoft import EdgeChromiumDriverManager


class BrowserController:
    def __init__(self) -> None:
        self.driver = self._build_driver()

    @staticmethod
    def _find_edge_binary() -> str | None:
        candidates = [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Microsoft", "Edge", "Application", "msedge.exe"),
            r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
            r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        ]
        for candidate in candidates:
            if candidate and os.path.exists(candidate):
                return candidate
        return None

    @staticmethod
    def _build_driver():
        edge_path = BrowserController._find_edge_binary()

        if edge_path:
            options = EdgeOptions()
            options.binary_location = edge_path
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1400,1200")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--user-agent=ReceiptAutofill")
            service = EdgeService(EdgeChromiumDriverManager().install())
            return webdriver.Edge(service=service, options=options)

        options = ChromeOptions()
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1400,1200")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--user-agent=ReceiptAutofill")
        service = ChromeService(ChromeDriverManager().install())
        return webdriver.Chrome(service=service, options=options)

    def open_url(self, url: str) -> None:
        self.driver.get(url)

    def fill_value(self, selector: str, value: str) -> bool:
        try:
            element = self.driver.find_element(By.CSS_SELECTOR, selector)
            element.clear()
            element.send_keys(value)
            return True
        except Exception:
            return False

    def fill_values(self, entries: Iterable[tuple[str, str]]) -> dict[str, bool]:
        result: dict[str, bool] = {}
        for selector, value in entries:
            result[selector] = self.fill_value(selector, value)
        return result

    def close(self) -> None:
        self.driver.quit()
