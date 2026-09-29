"""
storage.py — Media storage adapter for Lametna Basmeh.

Provides a single upload interface that:
  - Uses Cloudinary when all three env vars are set (CLOUDINARY_CLOUD_NAME,
    CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET).
  - Falls back to local filesystem (static/uploads/) in development when
    Cloudinary is not configured.
  - Raises UploadError on any failure so callers never silently use a partial URL.
  - Performs server-side file-type and size validation before upload.

Usage:
    from storage import upload_file, is_cloudinary_configured, ALLOWED_IMAGE_EXTENSIONS, UploadError

    try:
        url = upload_file(flask_file_storage_object, folder='photos')
    except UploadError as e:
        flash(str(e), 'danger')
"""
import os
import logging

from werkzeug.utils import secure_filename
from flask import current_app

logger = logging.getLogger(__name__)

# ── Allowed types ─────────────────────────────────────────────────────────────

ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_VIDEO_EXTENSIONS = {'mp4', 'webm', 'ogg', 'mov'}
ALLOWED_MEDIA_EXTENSIONS = ALLOWED_IMAGE_EXTENSIONS | ALLOWED_VIDEO_EXTENSIONS

# Maximum upload size enforced at the storage layer (redundant with Flask's
# MAX_CONTENT_LENGTH, but explicit for clarity).
MAX_UPLOAD_BYTES = 10 * 1024 * 1024  # 10 MB — covers video uploads


class UploadError(Exception):
    """Raised when an upload cannot be completed."""


def is_cloudinary_configured() -> bool:
    """Return True only if all three Cloudinary env vars are present and non-empty."""
    return all([
        os.environ.get('CLOUDINARY_CLOUD_NAME', '').strip(),
        os.environ.get('CLOUDINARY_API_KEY', '').strip(),
        os.environ.get('CLOUDINARY_API_SECRET', '').strip(),
    ])


def _get_extension(filename: str) -> str:
    """Return lowercase extension without dot, or empty string."""
    if '.' not in filename:
        return ''
    return filename.rsplit('.', 1)[-1].lower()


def _validate_file(file_storage, allowed_extensions: set) -> str:
    """
    Validate file type and (roughly) size.
    Returns the lowercase extension.
    Raises UploadError on rejection.
    """
    filename = file_storage.filename or ''
    if not filename:
        raise UploadError('لم يتم تحديد ملف.')

    ext = _get_extension(filename)
    if ext not in allowed_extensions:
        raise UploadError(
            f'نوع الملف "{ext}" غير مدعوم. '
            f'الأنواع المسموح بها: {", ".join(sorted(allowed_extensions))}.'
        )

    # Seek to end to check size, then reset.
    file_storage.stream.seek(0, 2)
    size = file_storage.stream.tell()
    file_storage.stream.seek(0)
    if size > MAX_UPLOAD_BYTES:
        raise UploadError(
            f'حجم الملف ({size // (1024*1024)} MB) يتجاوز الحد المسموح به '
            f'({MAX_UPLOAD_BYTES // (1024*1024)} MB).'
        )

    return ext


def upload_file(file_storage, folder: str = 'uploads',
                allowed_extensions: set = None) -> str:
    """
    Upload a Werkzeug FileStorage object and return the persistent URL.

    If Cloudinary is configured → uploads to Cloudinary, returns secure_url.
    If not configured AND in development → saves to local static/uploads/,
      returns a Flask url_for('static', ...) URL.
    If not configured AND in production → raises UploadError so the caller
      knows the upload cannot proceed safely.

    Parameters
    ----------
    file_storage    : Werkzeug FileStorage (from request.files)
    folder          : Cloudinary folder (ignored for local fallback)
    allowed_extensions : set of lowercase extensions without dot.
                       Defaults to ALLOWED_MEDIA_EXTENSIONS.

    Returns
    -------
    str : Persistent URL to the uploaded file.

    Raises
    ------
    UploadError : on validation failure, configuration error, or upload error.
    """
    if allowed_extensions is None:
        allowed_extensions = ALLOWED_MEDIA_EXTENSIONS

    ext = _validate_file(file_storage, allowed_extensions)

    if is_cloudinary_configured():
        return _upload_to_cloudinary(file_storage, folder)
    else:
        is_dev = os.environ.get('FLASK_ENV', 'production').lower() == 'development'
        if is_dev:
            logger.warning(
                'Cloudinary is not configured — falling back to local filesystem. '
                'This is NOT safe for production (Render ephemeral disk).'
            )
            return _upload_to_local(file_storage, ext)
        else:
            # Production with no Cloudinary: block the upload loudly.
            raise UploadError(
                'تعذّر رفع الملف: إعداد Cloudinary غير مكتمل في بيئة الإنتاج. '
                'يرجى التواصل مع الإدارة الفنية.'
            )


def _upload_to_cloudinary(file_storage, folder: str) -> str:
    """Upload to Cloudinary; return secure_url or raise UploadError."""
    try:
        import cloudinary.uploader  # already imported at app level; safe here too
        result = cloudinary.uploader.upload(
            file_storage,
            folder=folder,
            resource_type='auto',
        )
        url = result.get('secure_url')
        if not url:
            raise UploadError('لم يتم الحصول على رابط من Cloudinary.')
        return url
    except UploadError:
        raise
    except Exception as exc:
        logger.error('Cloudinary upload failed: %s', exc)
        raise UploadError(f'فشل رفع الملف إلى Cloudinary: {exc}') from exc


def _upload_to_local(file_storage, ext: str) -> str:
    """Save file to local static/uploads/; return a /static/uploads/... URL path."""
    import secrets as _secrets
    upload_dir = current_app.config.get(
        'UPLOAD_FOLDER',
        os.path.join(current_app.root_path, 'static', 'uploads')
    )
    os.makedirs(upload_dir, exist_ok=True)

    safe_name = secure_filename(file_storage.filename or 'upload')
    # Add a random suffix to avoid overwriting same-name files
    rand = _secrets.token_hex(6)
    unique_name = f'{rand}_{safe_name}'
    dest = os.path.join(upload_dir, unique_name)
    file_storage.save(dest)
    # Return a root-relative URL path (works without a request context)
    return f'/static/uploads/{unique_name}'
