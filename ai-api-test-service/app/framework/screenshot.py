from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


OUTCOME_COLORS = {
    'success': (22, 163, 74),
    'failure': (220, 38, 38),
    'error': (185, 28, 28),
    'skip': (217, 119, 6),
}


def capture_screenshot(screenshot_dir, run_id, outcome, case_name, http=None, message=''):
    folder = Path(screenshot_dir)
    folder.mkdir(parents=True, exist_ok=True)
    http = http or {}
    color = OUTCOME_COLORS.get(outcome, (37, 99, 235))
    image = Image.new('RGB', (960, 540), (15, 23, 42))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 960, 64), fill=color)
    try:
        font = ImageFont.load_default()
    except OSError:
        font = None
    lines = [
        f'[{outcome}] {case_name or run_id}',
        f'{http.get("method") or ""} {http.get("url") or ""}',
        f'status={http.get("status_code")}  elapsed={http.get("elapsed_ms")}ms',
        f'message={message or "-"}',
        'response:',
        str(http.get('response_text') or '')[:1200],
    ]
    y = 80
    for line in lines:
        draw.text((24, y), str(line)[:120], fill=(248, 250, 252), font=font)
        y += 28
        if y > 500:
            break
    path = folder / f'{run_id}_{outcome}.png'
    image.save(path)
    return str(path)
