from flask import Blueprint, jsonify, request, send_file, session
from PIL import Image, ImageDraw, ImageFont
import io
import re
from datetime import datetime, timedelta
import arabic_reshaper
from bidi.algorithm import get_display

certificates_bp = Blueprint('certificates', __name__, url_prefix='/certificates')


def _parse_event_date(raw_date):
    """Parse event date string into a date object. Returns None on failure."""
    raw = str(raw_date).strip()
    for fmt in ('%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d', '%d-%m-%Y'):
        try:
            return datetime.strptime(raw, fmt).date()
        except (ValueError, TypeError):
            pass
    # Support short formats like 11/9 or 11-9
    try:
        parts = re.split(r'[/.\-]', raw)
        if len(parts) >= 2:
            d, m = int(parts[0]), int(parts[1])
            y = int(parts[2]) if len(parts) > 2 else datetime.now().year
            return datetime(y, m, d).date()
    except Exception:
        pass
    return None


@certificates_bp.route('/ping')
def ping():
    return jsonify({"status": "Certificates engine connected successfully!"})


@certificates_bp.route('/generate/<int:event_id>', methods=['GET'])
def generate(event_id):
    # ── 1. Authentication guard ──────────────────────────────────────────────
    if 'user_id' not in session:
        return jsonify({'error': 'Unauthorized: يجب تسجيل الدخول أولاً'}), 401

    # ── 2. Import models here to avoid circular imports at module level ──────
    from app import db, Volunteer, Event, EventRegistration

    volunteer = Volunteer.query.get(session['user_id'])
    if not volunteer:
        return jsonify({'error': 'Forbidden: المتطوع غير موجود'}), 403

    event = Event.query.get(event_id)
    if not event:
        return jsonify({'error': 'Not Found: الفعالية غير موجودة'}), 404

    # ── 3. Attendance verification ───────────────────────────────────────────
    registration = EventRegistration.query.filter_by(
        volunteer_id=volunteer.id,
        event_id=event.id
    ).first()

    if not registration or not registration.attended:
        return jsonify({
            'error': 'Forbidden: لم يتم تسجيل حضورك في هذه الفعالية أو لم يتم تأكيده بعد'
        }), 403

    # ── 4. Time-lock: certificate only available after midnight of the event day ──
    event_date = _parse_event_date(event.date)
    if event_date is None:
        return jsonify({'error': 'Server Error: تعذّر قراءة تاريخ الفعالية'}), 500

    # Unlock moment = 00:00:00 of the day AFTER the event
    unlock_date = event_date + timedelta(days=1)
    unlock_dt = datetime.combine(unlock_date, datetime.min.time())

    now = datetime.now()
    if now < unlock_dt:
        unlock_date_str = unlock_date.strftime('%Y-%m-%d')
        return jsonify({
            'error': f'Forbidden: الشهادة غير متاحة حتى منتصف ليل {unlock_date_str}'
        }), 403

    # ── 5. Resolve volunteer name and rank ───────────────────────────────────
    name = volunteer.name or ''
    rank = volunteer.position or (
        'متطوع معتمد' if volunteer.status == 'approved' else 'متطوع مسجل'
    )

    # ── 6. Pillow certificate generation ────────────────────────────────────
    try:
        img = Image.open('static/template.jpeg')
        font = ImageFont.truetype('static/font.ttf', 50)

        reshaped_name = arabic_reshaper.reshape(name)
        display_name = get_display(reshaped_name)

        reshaped_rank = arabic_reshaper.reshape(rank)
        display_rank = get_display(reshaped_rank)

        draw = ImageDraw.Draw(img)
        draw.text((950, 515), display_name, font=font, fill=(0, 0, 0), anchor="rt")
        draw.text((950, 585), display_rank, font=font, fill=(0, 0, 0), anchor="rt")

        buffer = io.BytesIO()
        img.save(buffer, format='JPEG')
        buffer.seek(0)

        safe_name = f"certificate_{volunteer.id}_{event_id}.jpg"
        return send_file(
            buffer,
            mimetype='image/jpeg',
            as_attachment=True,
            download_name=safe_name
        )

    except FileNotFoundError as e:
        return jsonify({'error': f'Server Error: ملف القالب أو الخط غير موجود — {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': f'Server Error: فشل توليد الشهادة — {str(e)}'}), 500
