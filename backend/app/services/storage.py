from __future__ import annotations

from io import BytesIO
from pathlib import Path, PurePosixPath

from flask import current_app
from werkzeug.datastructures import FileStorage


def _safe_object_name(name: str) -> str:
    value = str(PurePosixPath(name.replace("\\", "/"))).lstrip("/")
    if not value or value.startswith("../") or "/../" in f"/{value}/":
        raise ValueError("Ruta de archivo inválida")
    return value


def _bucket():
    bucket_name = current_app.config.get("STORAGE_BUCKET")
    if not bucket_name:
        return None
    from google.cloud import storage

    return storage.Client().bucket(bucket_name)


def save_upload(uploaded: FileStorage, object_name: str) -> str:
    object_name = _safe_object_name(object_name)
    bucket = _bucket()
    if bucket is not None:
        blob = bucket.blob(object_name)
        uploaded.stream.seek(0)
        blob.upload_from_file(
            uploaded.stream,
            content_type=uploaded.mimetype or "application/octet-stream",
            rewind=True,
        )
    else:
        file_path = Path(current_app.config["BASE_DIR"]) / "uploads" / Path(object_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        uploaded.save(file_path)
    return f"/uploads/{object_name}"


def save_bytes(payload: bytes, object_name: str, content_type: str = "application/octet-stream", *, only_if_missing: bool = False) -> str:
    object_name = _safe_object_name(object_name)
    bucket = _bucket()
    if bucket is not None:
        blob = bucket.blob(object_name)
        if not only_if_missing or not blob.exists():
            blob.upload_from_string(payload, content_type=content_type)
    else:
        file_path = Path(current_app.config["BASE_DIR"]) / "uploads" / Path(object_name)
        file_path.parent.mkdir(parents=True, exist_ok=True)
        if not only_if_missing or not file_path.exists():
            file_path.write_bytes(payload)
    return f"/uploads/{object_name}"


def delete_object_url(url: str | None) -> None:
    if not url or not url.startswith("/uploads/"):
        return
    object_name = _safe_object_name(url.removeprefix("/uploads/"))
    bucket = _bucket()
    if bucket is not None:
        blob = bucket.blob(object_name)
        if blob.exists():
            blob.delete()
        return
    file_path = Path(current_app.config["BASE_DIR"]) / "uploads" / Path(object_name)
    if file_path.is_file():
        file_path.unlink()


def download_object(object_name: str) -> tuple[BytesIO, str, str]:
    object_name = _safe_object_name(object_name)
    bucket = _bucket()
    if bucket is not None:
        blob = bucket.blob(object_name)
        if not blob.exists():
            raise FileNotFoundError(object_name)
        payload = BytesIO(blob.download_as_bytes())
        return payload, blob.content_type or "application/octet-stream", PurePosixPath(object_name).name

    file_path = Path(current_app.config["BASE_DIR"]) / "uploads" / Path(object_name)
    if not file_path.is_file():
        raise FileNotFoundError(object_name)
    return BytesIO(file_path.read_bytes()), "application/octet-stream", file_path.name
