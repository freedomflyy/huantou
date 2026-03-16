from __future__ import annotations

import json
import os
import time
from pathlib import Path
import sys
import urllib.request

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


def load_env() -> None:
    env_path = ROOT_DIR / ".env"
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if not line or line.strip().startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


def _build_cos_client():
    from qcloud_cos import CosConfig, CosS3Client

    cfg = CosConfig(
        Region=os.environ["COS_REGION"],
        SecretId=os.environ["COS_SECRET_ID"],
        SecretKey=os.environ["COS_SECRET_KEY"],
        Scheme="https",
    )
    return CosS3Client(cfg)


def test_text_moderation() -> dict:
    client = _build_cos_client()
    bucket = os.environ["COS_BUCKET"]

    # CI SDK 的 Content 参数会在内部再次做 base64，因此这里传 bytes。
    resp = client.ci_auditing_text_submit(
        Bucket=bucket,
        Content="这是一条文本审核测试内容，含广告标识 vx123456".encode("utf-8"),
        DetectType=1 | 8,
        CallbackVersion="Detail",
    )
    data = resp.get("JobsDetail", {})
    return {
        "ok": True,
        "data": {
            "Label": data.get("Label"),
            "State": data.get("State"),
            "JobId": data.get("JobId"),
            "RequestId": resp.get("RequestId"),
        },
    }


def test_image_moderation() -> dict:
    client = _build_cos_client()
    bucket = os.environ["COS_BUCKET"]
    image_url = os.environ.get(
        "MODERATION_TEST_IMAGE_URL",
        "https://ark-project.tos-cn-beijing.volces.com/doc_image/seedream4_imageToimage.png",
    )

    # 走文档中的图片批量审核接口，避免 TMS/IMS 资源线混用。
    resp = client.ci_auditing_image_batch(
        Bucket=bucket,
        Input=[{"Url": image_url}],
        DetectType=1,
        Async=0,
    )
    details = (resp.get("JobsDetail") or [{}])[0]

    # 再补一条对象审核：上传到 COS 后再按 Object 识别，接近自动审核链路。
    object_result = {}
    try:
        img_bytes = urllib.request.urlopen(image_url, timeout=20).read()
        key = f"test/audit-check/{int(time.time())}.png"
        client.put_object(Bucket=bucket, Key=key, Body=img_bytes, ContentType="image/png")
        object_resp = client.get_object_sensitive_content_recognition(
            Bucket=bucket,
            Key=key,
            DetectType=1,
            Async=0,
        )
        object_result = {
            "key": key,
            "state": object_resp.get("State"),
            "label": object_resp.get("Label"),
        }
    except Exception as exc:
        object_result = {"error": str(exc)}

    return {
        "ok": True,
        "data": {
            "Label": details.get("Label"),
            "State": details.get("State"),
            "Code": details.get("Code"),
            "RequestId": resp.get("RequestId"),
            "object_test": object_result,
        },
    }


def main() -> None:
    load_env()
    result = {
        "text_moderation": {"ok": False, "error": ""},
        "image_moderation": {"ok": False, "error": ""},
    }

    try:
        result["text_moderation"] = test_text_moderation()
    except Exception as exc:
        result["text_moderation"] = {"ok": False, "error": str(exc)}

    try:
        result["image_moderation"] = test_image_moderation()
    except Exception as exc:
        result["image_moderation"] = {"ok": False, "error": str(exc)}

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
