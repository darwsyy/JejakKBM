"""Penghubung sederhana antara GUI Flet dan backend FastAPI."""

import os

import httpx


API_URL = os.getenv("JEJAKKBM_API_URL", "http://127.0.0.1:8000")


class ApiClient:
    def __init__(self):
        self.token = None

    def request(self, method, path, data=None, params=None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = httpx.request(
                method,
                f"{API_URL}{path}",
                json=data,
                params=params,
                headers=headers,
                timeout=15,
            )
        except httpx.RequestError as error:
            raise RuntimeError(
                "Backend belum berjalan. Jalankan FastAPI di port 8000 terlebih dahulu."
            ) from error

        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"{response.status_code}: {detail}")

        if response.status_code == 204 or not response.content:
            return None
        return response.json()

    def get(self, path, params=None):
        return self.request("GET", path, params=params)

    def download(self, path, params=None):
        headers = {"Authorization": f"Bearer {self.token}"} if self.token else {}
        try:
            response = httpx.get(
                f"{API_URL}{path}",
                params=params,
                headers=headers,
                timeout=30,
            )
        except httpx.RequestError as error:
            raise RuntimeError(
                "Backend belum berjalan. Jalankan FastAPI di port 8000 terlebih dahulu."
            ) from error
        if response.status_code >= 400:
            try:
                detail = response.json().get("detail", response.text)
            except ValueError:
                detail = response.text
            raise RuntimeError(f"{response.status_code}: {detail}")
        return response.content

    def post(self, path, data):
        return self.request("POST", path, data=data)

    def put(self, path, data=None):
        return self.request("PUT", path, data=data)
