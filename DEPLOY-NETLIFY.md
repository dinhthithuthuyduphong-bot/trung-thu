# ĐƯA WEBSITE LÊN MẠNG BẰNG NETLIFY

Đây là cách đơn giản nhất để lấy URL thật cho thiệp.

## Bước 1 — Giải nén
Giải nén file `trung-thu-cho-em-website.zip`.

Bạn sẽ có thư mục:

`trung-thu-cho-em/`

Bên trong phải nhìn thấy trực tiếp:
- index.html
- style.css
- script.js
- assets/

## Bước 2 — Đưa lên Netlify
1. Mở: https://app.netlify.com/drop
2. Đăng nhập Netlify.
3. Kéo THƯ MỤC `trung-thu-cho-em` vào vùng upload.
4. Netlify sẽ publish trang và cấp URL dạng:

`https://ten-ngau-nhien.netlify.app`

Đó chính là URL thật của thiệp.

## Bước 3 — Kiểm tra
Mở URL trên điện thoại và thử:
- nút Mở thiệp
- nhạc nền
- gallery
- video YouTube
- pause video / resume nhạc
- phần kết

## Bước 4 — Tạo QR chính thức
Sau khi đã có URL thật:

1. Mở file `create_qr.py`
2. Tìm:
   `WEBSITE_URL = "https://your-thank-you-card.com"`
3. Đổi thành URL Netlify của bạn.
4. Chạy:
   `python create_qr.py`

Sau đó sẽ có:
- `qr-code.png`
- `thiep-qr-in-10x15cm-url-moi.png`

Chỉ nên in thiệp sau khi đã tạo QR từ URL thật.

## Cập nhật website sau này
Nếu dùng Netlify Drag & Drop:
1. Sửa file trên máy.
2. Vào project trên Netlify.
3. Vào phần Deploys.
4. Kéo lại thư mục website đã sửa vào khu vực deploy.

URL chính vẫn có thể giữ nguyên, vì vậy QR đã in không cần đổi.

## Lưu ý về font
Website không dùng Google Fonts hay font tải ngoài.
Nó dùng font hệ thống:
- Arial / Helvetica / system-ui
- Times New Roman / serif

Nhờ vậy tiếng Việt hiển thị ổn định hơn trên Windows, iPhone, Android và macOS.
