"""
Best-effort EXIF metadata extractor. Never raises — returns a partial dict on any failure.
Supports JPEG, PNG, WebP, and HEIC/HEIF (via pillow-heif).
"""
import logging
from datetime import datetime
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

# Register pillow-heif so Pillow can open HEIC/HEIF files
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass


def _rational_to_float(rational) -> Optional[float]:
    """Convert a Pillow IFDRational or (numerator, denominator) tuple to float."""
    try:
        if hasattr(rational, "numerator") and hasattr(rational, "denominator"):
            denom = rational.denominator
            return float(rational.numerator) / float(denom) if denom else None
        if isinstance(rational, tuple) and len(rational) == 2:
            num, denom = rational
            return float(num) / float(denom) if denom else None
        return float(rational)
    except Exception:
        return None


def _dms_to_decimal(
    dms,
    ref: str,
) -> Optional[float]:
    """Convert degrees/minutes/seconds + hemisphere ref to signed decimal degrees."""
    try:
        degrees = _rational_to_float(dms[0])
        minutes = _rational_to_float(dms[1])
        seconds = _rational_to_float(dms[2])
        if degrees is None or minutes is None or seconds is None:
            return None
        decimal = degrees + minutes / 60.0 + seconds / 3600.0
        if ref in ("S", "W"):
            decimal = -decimal
        return round(decimal, 7)
    except Exception:
        return None


def _parse_exif_datetime(value: str) -> Optional[datetime]:
    """Parse EXIF datetime string 'YYYY:MM:DD HH:MM:SS' to datetime."""
    try:
        return datetime.strptime(value.strip(), "%Y:%m:%d %H:%M:%S")
    except Exception:
        return None


def extract_photo_metadata(file_path: str) -> Dict[str, Any]:
    """
    Extract EXIF/image metadata from a photo file.

    Returns a dict with keys:
        datetime_taken, latitude, longitude, altitude,
        camera_make, camera_model, width, height

    All values are None if not available. Never raises.
    """
    result: Dict[str, Any] = {
        "datetime_taken": None,
        "latitude": None,
        "longitude": None,
        "altitude": None,
        "camera_make": None,
        "camera_model": None,
        "width": None,
        "height": None,
    }

    try:
        from PIL import Image
        from PIL.ExifTags import TAGS, GPSTAGS

        with Image.open(file_path) as img:
            result["width"] = img.width
            result["height"] = img.height

            # getexif() works for JPEG/WebP/PNG/HEIC
            exif_data = img.getexif()
            if not exif_data:
                return result

            # Build a human-readable tag map
            tag_map: Dict[str, Any] = {}
            for tag_id, value in exif_data.items():
                tag_name = TAGS.get(tag_id, str(tag_id))
                tag_map[tag_name] = value

            result["camera_make"] = tag_map.get("Make") or None
            result["camera_model"] = tag_map.get("Model") or None

            raw_dt = tag_map.get("DateTimeOriginal") or tag_map.get("DateTime")
            if raw_dt:
                result["datetime_taken"] = _parse_exif_datetime(str(raw_dt))

            # GPS data lives under tag 34853 (GPSInfo)
            gps_ifd_tag = next(
                (tag_id for tag_id, name in TAGS.items() if name == "GPSInfo"), None
            )
            if gps_ifd_tag and gps_ifd_tag in exif_data:
                gps_ifd = exif_data.get_ifd(gps_ifd_tag)
                gps: Dict[str, Any] = {}
                for tag_id, value in gps_ifd.items():
                    gps[GPSTAGS.get(tag_id, str(tag_id))] = value

                lat_dms = gps.get("GPSLatitude")
                lat_ref = gps.get("GPSLatitudeRef", "N")
                lon_dms = gps.get("GPSLongitude")
                lon_ref = gps.get("GPSLongitudeRef", "E")

                if lat_dms and lon_dms:
                    result["latitude"] = _dms_to_decimal(lat_dms, lat_ref)
                    result["longitude"] = _dms_to_decimal(lon_dms, lon_ref)

                alt_rational = gps.get("GPSAltitude")
                if alt_rational is not None:
                    alt = _rational_to_float(alt_rational)
                    alt_ref = gps.get("GPSAltitudeRef", 0)
                    if alt is not None:
                        result["altitude"] = round(-alt if alt_ref == 1 else alt, 2)

    except Exception as exc:
        logger.debug("EXIF extraction failed for %s: %s", file_path, exc)

    return result
