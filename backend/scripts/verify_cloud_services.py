from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.core.config import settings


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_sts() -> CheckResult:
    try:
        from tencentcloud.common import credential
        from tencentcloud.sts.v20180813 import models, sts_client
    except Exception as exc:
        return CheckResult("sts", False, f"dependency error: {exc}")

    if not settings.cos_secret_id or not settings.cos_secret_key:
        return CheckResult("sts", False, "missing COS_SECRET_ID/COS_SECRET_KEY")

    try:
        cred = credential.Credential(settings.cos_secret_id, settings.cos_secret_key)
        client = sts_client.StsClient(cred, settings.tencentcloud_region)
        req = models.GetCallerIdentityRequest()
        resp = client.GetCallerIdentity(req)
        data = json.loads(resp.to_json_string())
        return CheckResult("sts", True, f"account={data.get('AccountId')}")
    except Exception as exc:
        return CheckResult("sts", False, str(exc))


def check_cos() -> CheckResult:
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except Exception as exc:
        return CheckResult("cos", False, f"dependency error: {exc}")

    if not settings.cos_secret_id or not settings.cos_secret_key:
        return CheckResult("cos", False, "missing COS_SECRET_ID/COS_SECRET_KEY")
    if not settings.cos_bucket or not settings.cos_region:
        return CheckResult("cos", False, "missing COS_BUCKET/COS_REGION")

    try:
        config = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
            Scheme="https",
        )
        client = CosS3Client(config)
        resp = client.head_bucket(Bucket=settings.cos_bucket)
        region = resp.get("x-cos-bucket-region", "unknown")
        return CheckResult("cos", True, f"bucket={settings.cos_bucket}, region={region}")
    except Exception as exc:
        return CheckResult("cos", False, str(exc))


def check_moderation_ci() -> CheckResult:
    try:
        from qcloud_cos import CosConfig, CosS3Client
    except Exception as exc:
        return CheckResult("moderation_ci", False, f"dependency error: {exc}")

    if not settings.cos_secret_id or not settings.cos_secret_key:
        return CheckResult("moderation_ci", False, "missing COS_SECRET_ID/COS_SECRET_KEY")
    if not settings.cos_bucket or not settings.cos_region:
        return CheckResult("moderation_ci", False, "missing COS_BUCKET/COS_REGION")

    try:
        cfg = CosConfig(
            Region=settings.cos_region,
            SecretId=settings.cos_secret_id,
            SecretKey=settings.cos_secret_key,
            Scheme="https",
        )
        client = CosS3Client(cfg)
        resp = client.ci_auditing_text_submit(
            Bucket=settings.cos_bucket,
            Content="连通性测试：这是一条审核测试文本".encode("utf-8"),
            DetectType=1 | 8,
            CallbackVersion="Simple",
        )
        detail = resp.get("JobsDetail", {})
        return CheckResult("moderation_ci", True, f"state={detail.get('State')}, label={detail.get('Label')}")
    except Exception as exc:
        return CheckResult("moderation_ci", False, str(exc))


def main() -> None:
    checks = [check_sts(), check_cos(), check_moderation_ci()]
    for item in checks:
        flag = "OK" if item.ok else "FAIL"
        print(f"[{flag}] {item.name}: {item.detail}")


if __name__ == "__main__":
    main()
