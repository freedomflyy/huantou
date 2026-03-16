from __future__ import annotations

import base64
import json
import os
import time
from pathlib import Path
import sys

from qcloud_cos import CosConfig, CosS3Client

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


def main() -> None:
    load_env()
    secret_id = os.environ["COS_SECRET_ID"]
    secret_key = os.environ["COS_SECRET_KEY"]
    region = os.environ["COS_REGION"]
    bucket = os.environ["COS_BUCKET"]

    config = CosConfig(
        Region=region,
        SecretId=secret_id,
        SecretKey=secret_key,
        Scheme="https",
    )
    client = CosS3Client(config)

    stamp = int(time.time())
    prefix = f"test/audit-check/{stamp}"
    text_key = f"{prefix}/hello.txt"
    img_key = f"{prefix}/tiny.png"

    png_base64 = (
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO9W8a8AAAAASUVORK5CYII="
    )
    png_bytes = base64.b64decode(png_base64)

    put_text = client.put_object(Bucket=bucket, Key=text_key, Body="cos upload test")
    put_img = client.put_object(
        Bucket=bucket,
        Key=img_key,
        Body=png_bytes,
        ContentType="image/png",
    )

    head_text = client.head_object(Bucket=bucket, Key=text_key)
    head_img = client.head_object(Bucket=bucket, Key=img_key)
    text_obj = client.get_object(Bucket=bucket, Key=text_key)
    text_body = text_obj["Body"].get_raw_stream().read().decode("utf-8")

    result = {
        "bucket": bucket,
        "text_key": text_key,
        "img_key": img_key,
        "put_text_etag": put_text.get("ETag"),
        "put_img_etag": put_img.get("ETag"),
        "head_text_content_length": head_text.get("Content-Length"),
        "head_img_content_type": head_img.get("Content-Type"),
        "read_back_text": text_body,
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

