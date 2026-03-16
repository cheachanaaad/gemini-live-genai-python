import asyncio
import base64
import json
import logging
from io import BytesIO

from google import genai
from google.genai import types
from PIL import Image

logger = logging.getLogger(__name__)


class ItemImageSegmenter:
    def __init__(self, api_key, model="gemini-2.5-flash"):
        self.api_key = api_key
        self.model = model
        self.client = genai.Client(
            api_key=api_key,
            http_options={"api_version": "v1alpha"},
        )

    async def segment_items(self, frame_b64, requested_items):
        if not frame_b64 or not requested_items:
            return {}
        return await asyncio.to_thread(
            self._segment_items_sync,
            frame_b64,
            requested_items,
        )

    def _segment_items_sync(self, frame_b64, requested_items):
        frame_bytes = base64.b64decode(frame_b64)
        image = Image.open(BytesIO(frame_bytes)).convert("RGBA")
        normalized_lookup = {
            self._normalize_name(name): name for name in requested_items if name
        }
        prompt = {
            "task": "Locate requested grocery items in the provided image.",
            "requirements": [
                "Return JSON only.",
                "For each visible requested item, return one detection.",
                "Use box_2d normalized to 0-1000 integers in [ymin, xmin, ymax, xmax].",
                "If possible, also return mask_png_base64 as a grayscale PNG mask for the object inside the bounding box.",
                "If an item is not visible, omit it.",
            ],
            "requested_items": requested_items,
            "response_schema": {
                "detections": [
                    {
                        "requested_name": "string",
                        "matched_name": "string",
                        "box_2d": [0, 0, 0, 0],
                        "mask_png_base64": "string",
                        "confidence": 0.0,
                    }
                ]
            },
        }

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                types.Part.from_bytes(data=frame_bytes, mime_type="image/jpeg"),
                json.dumps(prompt, ensure_ascii=False),
            ],
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
            ),
        )
        parsed = self._safe_parse_json(getattr(response, "text", "") or "{}")
        detections = parsed.get("detections", [])
        segmented_images = {}

        for detection in detections:
            requested_name = normalized_lookup.get(
                self._normalize_name(detection.get("requested_name"))
            )
            if not requested_name:
                continue

            box = detection.get("box_2d")
            if not self._valid_box(box):
                continue

            try:
                image_b64 = self._build_segmented_image(
                    source_image=image,
                    box_2d=box,
                    mask_b64=detection.get("mask_png_base64", ""),
                )
            except Exception:
                logger.exception("Failed to build segmented image for %s", requested_name)
                continue

            segmented_images[self._normalize_name(requested_name)] = {
                "image": image_b64,
                "mime_type": "image/png"
                if detection.get("mask_png_base64", "")
                else "image/jpeg",
                "box_2d": box,
                "matched_name": detection.get("matched_name") or requested_name,
                "confidence": detection.get("confidence"),
            }

        logger.info(
            "ItemImageSegmenter segmented requested=%s matched=%s",
            len(requested_items),
            len(segmented_images),
        )
        return segmented_images

    def _build_segmented_image(self, source_image, box_2d, mask_b64=""):
        cropped = self._crop_by_box(source_image, box_2d).convert("RGBA")

        if mask_b64:
            mask = Image.open(BytesIO(base64.b64decode(mask_b64))).convert("L")
            if mask.size != cropped.size:
                mask = mask.resize(cropped.size)
            cropped.putalpha(mask)
            output = BytesIO()
            cropped.save(output, format="PNG")
            return base64.b64encode(output.getvalue()).decode("utf-8")

        output = BytesIO()
        cropped.convert("RGB").save(output, format="JPEG", quality=90)
        return base64.b64encode(output.getvalue()).decode("utf-8")

    def _crop_by_box(self, image, box_2d):
        width, height = image.size
        ymin, xmin, ymax, xmax = box_2d
        left = max(0, int(xmin / 1000 * width))
        top = max(0, int(ymin / 1000 * height))
        right = min(width, int(xmax / 1000 * width))
        bottom = min(height, int(ymax / 1000 * height))
        if right <= left or bottom <= top:
            raise ValueError(f"Invalid crop box: {box_2d}")
        return image.crop((left, top, right, bottom))

    def _safe_parse_json(self, payload):
        try:
            return json.loads(payload)
        except json.JSONDecodeError:
            logger.exception("Failed to parse segmentation JSON")
            return {}

    def _normalize_name(self, value):
        return " ".join((value or "").strip().split()).lower()

    def _valid_box(self, value):
        return (
            isinstance(value, list)
            and len(value) == 4
            and all(isinstance(number, (int, float)) for number in value)
        )
