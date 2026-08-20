import os
import stat
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

MIN_EDGE_SECRET_BYTES = 32
MAX_EDGE_SECRET_BYTES = 512


def _validate_secret(secret: bytes, source: str) -> bytes:
    if not MIN_EDGE_SECRET_BYTES <= len(secret) <= MAX_EDGE_SECRET_BYTES:
        raise ImproperlyConfigured(
            f"{source} must contain between {MIN_EDGE_SECRET_BYTES} and {MAX_EDGE_SECRET_BYTES} bytes."
        )
    if any(byte < 33 or byte > 126 for byte in secret):
        raise ImproperlyConfigured(f"{source} must contain printable ASCII without whitespace.")
    return secret


def _validate_file_permissions(metadata: os.stat_result) -> None:
    permissions = stat.S_IMODE(metadata.st_mode)
    effective_uid = os.geteuid()
    owner_only = metadata.st_uid == effective_uid and permissions in {0o400, 0o600}
    root_group_readable = metadata.st_uid == 0 and metadata.st_gid == 0 and os.getegid() == 0 and permissions == 0o640
    if not owner_only and not root_group_readable:
        raise ImproperlyConfigured(
            "PILGRIMAGE_SSO_EDGE_SECRET_FILE must be owned by the runtime user with mode 0400/0600, "
            "or by root:root with mode 0640 while the runtime effective group is 0."
        )


def _read_secret_file(path_value: str) -> bytes:
    path = Path(path_value)
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE cannot be read.") from exc

    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE must be a regular file, not a symlink.")
    _validate_file_permissions(metadata)
    if metadata.st_size > MAX_EDGE_SECRET_BYTES + 2:
        raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE is unexpectedly large.")

    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE cannot be opened safely.") from exc
    try:
        opened_metadata = os.fstat(descriptor)
        if not stat.S_ISREG(opened_metadata.st_mode):
            raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE must be a regular file.")
        if (metadata.st_dev, metadata.st_ino) != (opened_metadata.st_dev, opened_metadata.st_ino):
            raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET_FILE changed while it was opened.")
        _validate_file_permissions(opened_metadata)
        secret = os.read(descriptor, MAX_EDGE_SECRET_BYTES + 3)
    finally:
        os.close(descriptor)

    return _validate_secret(secret.rstrip(b"\r\n"), "PILGRIMAGE_SSO_EDGE_SECRET_FILE")


def load_edge_secret(*, enabled: bool, file_path: str, fallback: str) -> bytes:
    if not enabled:
        return b""
    if file_path:
        return _read_secret_file(file_path)
    if fallback:
        try:
            value = fallback.encode("ascii")
        except UnicodeEncodeError as exc:
            raise ImproperlyConfigured("PILGRIMAGE_SSO_EDGE_SECRET must contain printable ASCII.") from exc
        return _validate_secret(value, "PILGRIMAGE_SSO_EDGE_SECRET")
    raise ImproperlyConfigured("SSO mode requires PILGRIMAGE_SSO_EDGE_SECRET_FILE or PILGRIMAGE_SSO_EDGE_SECRET.")
