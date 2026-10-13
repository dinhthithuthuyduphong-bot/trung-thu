from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import qrcode

# EDIT QR URL HERE
WEBSITE_URL = "https://your-thank-you-card.com"

root = Path(__file__).parent

qr = qrcode.QRCode(
    error_correction=qrcode.constants.ERROR_CORRECT_H,
    box_size=14,
    border=5
)
qr.add_data(WEBSITE_URL)
qr.make(fit=True)
qr_img = qr.make_image(fill_color="#35131d", back_color="#fffdf8").convert("RGB")
qr_img.save(root / "qr-code.png")

# Tạo lại thiệp raster 10x15 cm 300 DPI với QR mới
W, H = 1181, 1772
img = Image.new("RGB", (W, H), "#fff8ea")
draw = ImageDraw.Draw(img)

def pick_font(candidates, size):
    for path in candidates:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()

REGULAR = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/System/Library/Fonts/Supplemental/Arial.ttf",
]
BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
]
SERIF = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
    "C:/Windows/Fonts/georgia.ttf",
    "/System/Library/Fonts/Supplemental/Georgia.ttf",
]
SERIF_BOLD = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
    "C:/Windows/Fonts/georgiab.ttf",
    "/System/Library/Fonts/Supplemental/Georgia Bold.ttf",
]

def F(kind, size):
    mapping = {"regular": REGULAR, "bold": BOLD, "serif": SERIF, "serif_bold": SERIF_BOLD}
    return pick_font(mapping[kind], size)
def center(text, y, font, fill):
    box = draw.textbbox((0,0), text, font=font)
    draw.text(((W-(box[2]-box[0]))/2, y), text, font=font, fill=fill)

draw.rounded_rectangle((48,48,W-48,H-48), radius=42, fill="#fffdf8", outline="#d8b264", width=3)
draw.rounded_rectangle((48,48,W-48,520), radius=42, fill="#5d1e2f")
draw.rectangle((48,450,W-48,520), fill="#5d1e2f")
draw.ellipse((W//2-110,108,W//2+110,328), fill="#f2dfad")
draw.ellipse((W//2-35,82,W//2+155,282), fill="#5d1e2f")

center("LỜI CẢM ƠN", 352, F("serif_bold",74), "#fff8ea")
center("MỘT MÙA TRĂNG · MỘT VÒNG TAY", 453, F("bold",24), "#f2dfad")
center("Một hạt giống thiện gieo xuống,", 600, F("serif",34), "#5d1e2f")
center("vạn nụ cười an vui nở rộ.", 654, F("serif",34), "#5d1e2f")

q = qr_img.resize((470,470), Image.Resampling.NEAREST)
qx=(W-470)//2; qy=750
draw.rounded_rectangle((qx-24,qy-24,qx+494,qy+494), radius=24, fill="#fffdf8", outline="#eadbb8", width=2)
img.paste(q,(qx,qy))

center("Quét mã để cùng nhìn lại hành trình", 1284, F("bold",28), "#35131d")
center("đáng nhớ của chúng ta.", 1328, F("bold",28), "#35131d")
center(WEBSITE_URL, 1392, F("regular",18), "#7a6c62")
draw.line((260,1490,W-260,1490), fill="#d8b264", width=2)
center("TRUNG THU CHO EM", 1535, F("bold",28), "#8a2f3f")
center("Gửi một mùa trăng ấm áp bằng những tấm lòng biết sẻ chia.", 1592, F("regular",22), "#7a6c62")
img.save(root/"thiep-qr-in-10x15cm-url-moi.png", dpi=(300,300), quality=95)

print("Đã tạo QR cho:", WEBSITE_URL)
