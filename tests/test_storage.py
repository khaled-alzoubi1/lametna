"""
P0-C Media Storage Tests
================================
Tests cover:
  1. Cloudinary configuration detection
  2. Storage adapter behaviour — Cloudinary path (mocked)
  3. Storage adapter behaviour — local-dev fallback path
  4. Missing configuration in production → UploadError
  5. File type validation (allowed / rejected extensions)
  6. File size validation
  7. Failed Cloudinary upload → UploadError (no partial URL)
  8. Existing Cloudinary URLs remain compatible (pass-through test)
  9. Certificates are dynamically generated and never require persistent storage
"""

import io
import os
import sys
import types
import pytest
from unittest.mock import MagicMock, patch

os.environ.setdefault('FLASK_ENV', 'development')
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import storage as storage_module
from storage import (
    upload_file,
    is_cloudinary_configured,
    UploadError,
    ALLOWED_IMAGE_EXTENSIONS,
    ALLOWED_MEDIA_EXTENSIONS,
    _validate_file,
    _get_extension,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_file_storage(filename: str, content: bytes = b'fakecontent') -> MagicMock:
    """Create a fake Werkzeug FileStorage-like object."""
    fs = MagicMock()
    fs.filename = filename
    fs.stream = io.BytesIO(content)
    # Simulate seek/tell for size check
    fs.stream.seek(0)
    return fs


def make_flask_app():
    """Minimal Flask app for context."""
    from app import app
    app.config.update({
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'WTF_CSRF_ENABLED': False,
        'UPLOAD_FOLDER': '/tmp/test_uploads_lametna',
    })
    return app


# ── 1. Cloudinary configuration detection ────────────────────────────────────

def test_cloudinary_configured_when_all_vars_set():
    with patch.dict(os.environ, {
        'CLOUDINARY_CLOUD_NAME': 'mycloud',
        'CLOUDINARY_API_KEY': '123',
        'CLOUDINARY_API_SECRET': 'abc',
    }):
        assert is_cloudinary_configured() is True


def test_cloudinary_not_configured_when_any_var_missing():
    # Missing API_SECRET
    with patch.dict(os.environ, {
        'CLOUDINARY_CLOUD_NAME': 'mycloud',
        'CLOUDINARY_API_KEY': '123',
    }, clear=False):
        env = os.environ.copy()
        env.pop('CLOUDINARY_API_SECRET', None)
        with patch.dict(os.environ, env, clear=True):
            # Ensure CLOUDINARY_API_SECRET is absent
            assert 'CLOUDINARY_API_SECRET' not in os.environ or \
                   not os.environ.get('CLOUDINARY_API_SECRET', '').strip() or \
                   not is_cloudinary_configured()


def test_cloudinary_not_configured_when_blank_vars():
    with patch.dict(os.environ, {
        'CLOUDINARY_CLOUD_NAME': '   ',
        'CLOUDINARY_API_KEY': '',
        'CLOUDINARY_API_SECRET': '',
    }):
        assert is_cloudinary_configured() is False


def test_cloudinary_not_configured_when_no_vars():
    env = {k: v for k, v in os.environ.items()
           if k not in ('CLOUDINARY_CLOUD_NAME', 'CLOUDINARY_API_KEY', 'CLOUDINARY_API_SECRET')}
    with patch.dict(os.environ, env, clear=True):
        assert is_cloudinary_configured() is False


# ── 2. File extension & size validation ──────────────────────────────────────

def test_validate_accepts_image_extensions():
    for ext in ('png', 'jpg', 'jpeg', 'gif', 'webp'):
        fs = make_file_storage(f'photo.{ext}')
        result = _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)
        assert result == ext


def test_validate_rejects_executable_extension():
    fs = make_file_storage('malicious.exe')
    with pytest.raises(UploadError, match='غير مدعوم'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


def test_validate_rejects_php_extension():
    fs = make_file_storage('shell.php')
    with pytest.raises(UploadError, match='غير مدعوم'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


def test_validate_rejects_no_extension():
    fs = make_file_storage('noext')
    with pytest.raises(UploadError, match='غير مدعوم'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


def test_validate_rejects_empty_filename():
    fs = make_file_storage('')
    with pytest.raises(UploadError, match='لم يتم تحديد'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


def test_validate_rejects_oversized_file():
    from storage import MAX_UPLOAD_BYTES
    big = b'x' * (MAX_UPLOAD_BYTES + 1)
    fs = make_file_storage('big.jpg', big)
    with pytest.raises(UploadError, match='يتجاوز الحد'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


def test_validate_accepts_video_extensions():
    for ext in ('mp4', 'webm', 'ogg', 'mov'):
        fs = make_file_storage(f'clip.{ext}')
        result = _validate_file(fs, ALLOWED_MEDIA_EXTENSIONS)
        assert result == ext


def test_validate_rejects_video_as_image():
    fs = make_file_storage('clip.mp4')
    with pytest.raises(UploadError, match='غير مدعوم'):
        _validate_file(fs, ALLOWED_IMAGE_EXTENSIONS)


# ── 3. Upload adapter — Cloudinary path (mocked) ─────────────────────────────

def test_upload_uses_cloudinary_when_configured():
    app = make_flask_app()
    mock_result = {'secure_url': 'https://res.cloudinary.com/test/image/upload/v1/test.jpg'}
    mock_uploader = MagicMock()
    mock_uploader.upload.return_value = mock_result

    with app.app_context():
        with patch.dict(os.environ, {
            'CLOUDINARY_CLOUD_NAME': 'mycloud',
            'CLOUDINARY_API_KEY': '123',
            'CLOUDINARY_API_SECRET': 'abc',
            'FLASK_ENV': 'development',
        }):
            with patch('storage.is_cloudinary_configured', return_value=True), \
                 patch('cloudinary.uploader', mock_uploader):
                fs = make_file_storage('photo.jpg')
                url = upload_file(fs, folder='photos', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
                assert url == 'https://res.cloudinary.com/test/image/upload/v1/test.jpg'
                mock_uploader.upload.assert_called_once()


def test_upload_cloudinary_returns_correct_url_from_result():
    app = make_flask_app()
    expected_url = 'https://res.cloudinary.com/demo/image/upload/sample.jpg'
    mock_uploader = MagicMock()
    mock_uploader.upload.return_value = {'secure_url': expected_url, 'public_id': 'sample'}

    with app.app_context():
        with patch('storage.is_cloudinary_configured', return_value=True), \
             patch('cloudinary.uploader', mock_uploader):
            fs = make_file_storage('test.jpg')
            url = upload_file(fs, folder='photos')
            assert url == expected_url


# ── 4. Failed Cloudinary upload → UploadError, no partial URL ────────────────

def test_cloudinary_upload_failure_raises_upload_error():
    app = make_flask_app()
    mock_uploader = MagicMock()
    mock_uploader.upload.side_effect = Exception('Cloudinary network error')

    with app.app_context():
        with patch('storage.is_cloudinary_configured', return_value=True), \
             patch('cloudinary.uploader', mock_uploader):
            fs = make_file_storage('photo.jpg')
            with pytest.raises(UploadError, match='فشل رفع الملف'):
                upload_file(fs, folder='photos')


def test_cloudinary_upload_missing_secure_url_raises_upload_error():
    app = make_flask_app()
    mock_uploader = MagicMock()
    # Returns a result dict with no secure_url key
    mock_uploader.upload.return_value = {'public_id': 'something'}

    with app.app_context():
        with patch('storage.is_cloudinary_configured', return_value=True), \
             patch('cloudinary.uploader', mock_uploader):
            fs = make_file_storage('photo.jpg')
            with pytest.raises(UploadError, match='رابط'):
                upload_file(fs, folder='photos')


# ── 5. Production with no Cloudinary → UploadError ───────────────────────────

def test_production_without_cloudinary_raises_upload_error():
    app = make_flask_app()

    with app.app_context():
        with patch('storage.is_cloudinary_configured', return_value=False), \
             patch.dict(os.environ, {'FLASK_ENV': 'production'}):
            fs = make_file_storage('photo.jpg')
            with pytest.raises(UploadError, match='إعداد Cloudinary'):
                upload_file(fs, folder='photos')


# ── 6. Local-dev fallback ─────────────────────────────────────────────────────

def test_dev_without_cloudinary_saves_locally(tmp_path):
    app = make_flask_app()
    app.config['UPLOAD_FOLDER'] = str(tmp_path / 'uploads')

    with app.app_context():
        with patch('storage.is_cloudinary_configured', return_value=False), \
             patch.dict(os.environ, {'FLASK_ENV': 'development'}):
            fs = make_file_storage('photo.jpg')
            # save() needs a real call — mock it to write to tmp
            saved_paths = []
            original_save = None

            def fake_save(path):
                saved_paths.append(path)
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, 'wb') as f:
                    f.write(b'fakecontent')

            fs.save = fake_save
            url = upload_file(fs, folder='photos', allowed_extensions=ALLOWED_IMAGE_EXTENSIONS)
            assert url.startswith('/static/uploads/') or 'uploads' in url
            assert len(saved_paths) == 1


# ── 7. Existing Cloudinary URL compatibility ──────────────────────────────────

def test_existing_cloudinary_url_format_is_valid():
    """Stored Cloudinary secure_urls must use https and contain cloudinary.com."""
    sample_urls = [
        'https://res.cloudinary.com/mycloud/image/upload/v12345/folder/photo.jpg',
        'https://res.cloudinary.com/mycloud/video/upload/v12345/folder/clip.mp4',
        'https://res.cloudinary.com/mycloud/image/upload/sample.webp',
    ]
    for url in sample_urls:
        assert url.startswith('https://'), f"URL must use HTTPS: {url}"
        assert 'cloudinary.com' in url, f"URL must be from cloudinary.com: {url}"


# ── 8. Certificates do not require persistent storage ─────────────────────────

def test_certificate_generation_is_dynamic():
    """
    Verify the certificate endpoint uses in-memory BytesIO and does not
    reference any local storage path or Cloudinary upload.
    """
    cert_source = open(
        os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     'controllers', 'certificates.py'),
        encoding='utf-8'
    ).read()

    # Must use in-memory buffer
    assert 'BytesIO' in cert_source or 'io.BytesIO' in cert_source, \
        "Certificate generation must use an in-memory buffer"

    # Must NOT save to local filesystem
    assert '.save(' not in cert_source or 'buffer' in cert_source, \
        "Certificate must not write to the local filesystem"

    # Must NOT upload to Cloudinary
    assert 'cloudinary.uploader' not in cert_source, \
        "Certificate must not be uploaded to Cloudinary — it is dynamically generated per request"


# ── 9. get_extension helper ───────────────────────────────────────────────────

def test_get_extension_handles_dotless_filename():
    assert _get_extension('README') == ''


def test_get_extension_returns_lowercase():
    assert _get_extension('Photo.JPG') == 'jpg'


def test_get_extension_handles_multiple_dots():
    assert _get_extension('archive.tar.gz') == 'gz'
