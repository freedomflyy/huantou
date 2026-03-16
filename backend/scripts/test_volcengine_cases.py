from __future__ import annotations

import json
from pathlib import Path
import sys

import requests

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

BASE_URL = "http://127.0.0.1:8000/api/v1"
HEADERS = {"X-User-Id": "1", "Content-Type": "application/json"}


def main() -> None:
    cases = [
        {
            "name": "txt2img",
            "payload": {
                "task_type": "txt2img",
                "provider": "volcengine",
                "prompt": "星际穿越，黑洞，黑洞里冲出一辆快支离破碎的复古列车，电影大片，末日感，动感，对比色，光线追踪，动态模糊，景深，超现实主义",
                "params": {
                    "output_count": 4,
                },
            },
        },
        {
            "name": "img2img",
            "payload": {
                "task_type": "img2img",
                "provider": "volcengine",
                "prompt": "生成狗狗趴在草地上的近景画面",
                "input_image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimage.png",
                "params": {
                    "output_count": 4,
                },
            },
        },
        {
            "name": "style_transfer",
            "payload": {
                "task_type": "style_transfer",
                "provider": "volcengine",
                "prompt": "将图1的服装换为图2的服装",
                "input_image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imagesToimage_1.png",
                "reference_image_url": "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imagesToimage_2.png",
                "params": {
                    "output_count": 3,
                },
            },
        },
    ]

    results: list[dict] = []
    for case in cases:
        create = requests.post(
            f"{BASE_URL}/tasks",
            headers=HEADERS,
            json=case["payload"],
            timeout=30,
        )
        create_data = create.json()
        task_id = create_data.get("id")
        if create.status_code >= 300 or not task_id:
            results.append(
                {
                    "name": case["name"],
                    "create_status": create.status_code,
                    "create_data": create_data,
                }
            )
            continue

        executed = requests.post(
            f"{BASE_URL}/tasks/{task_id}/execute",
            headers=HEADERS,
            json={},
            timeout=180,
        )
        try:
            execute_data = executed.json()
        except Exception:
            execute_data = {"raw": executed.text}

        results.append(
            {
                "name": case["name"],
                "task_id": task_id,
                "create_status": create.status_code,
                "execute_status": executed.status_code,
                "execute_data": execute_data,
            }
        )

    balance = requests.get(
        f"{BASE_URL}/points/balance",
        headers={"X-User-Id": "1"},
        timeout=30,
    ).json()

    print(
        json.dumps(
            {
                "results": results,
                "balance": balance,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
