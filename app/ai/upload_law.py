
import httpx

LAW_FILE_PATH = r"C:\Users\User\AppData\Local\Temp\claude\C--Users-User\94369f80-0a66-47ea-8c78-14f87beb5651\scratchpad\labor_standards_act.txt"

with open(LAW_FILE_PATH, encoding="utf-8") as f:
    content = f.read()



BASE_URL = "http://127.0.0.1:8000"

login_resp = httpx.post(f"{BASE_URL}/auth/login", json={"username": "A0006", "password": "88888888"})
token = login_resp.json()["data"]["token"]

resp = httpx.post(
    f"{BASE_URL}/kb/documents",
    headers={"Authorization": f"Bearer {token}"},
    json={"title": "勞動基準法", "content": content, "type": "raw"},
)
print(resp.status_code)
print(resp.json())
print(login_resp.status_code, login_resp.json())