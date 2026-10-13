# TRUNG THU CHO EM — Thiệp cảm ơn tương tác

## Mở thử trên máy
Cách đơn giản nhất:
1. Giải nén toàn bộ thư mục.
2. Mở Terminal/Command Prompt tại thư mục này.
3. Chạy:
   python -m http.server 8000
4. Mở trình duyệt tại:
   http://localhost:8000

> Có thể mở index.html trực tiếp, nhưng một số trình duyệt hạn chế media/API khi chạy bằng file://.

## Nhạc nền
Website ưu tiên đường dẫn:
assets/music/background.mp3

Nếu chưa có MP3, website sẽ tự dùng file fallback nguyên bản đã kèm theo:
assets/music/trung-thu-ambient.wav

Hãy đặt file MP3 bạn có quyền sử dụng vào đúng vị trí và đúng tên trên.

Link NhacCuaTui được cung cấp là trang nghe nhạc, không phải URL file MP3 trực tiếp.
Vì vậy không nên nhúng link đó như audio source. Cách ổn định là dùng file MP3 hợp lệ
hoặc một nguồn audio trực tiếp mà bạn có quyền sử dụng.

## Video
Video hiện dùng YouTube:
https://www.youtube.com/watch?v=w6-zjCycdRs&t=2293s

Cấu hình trong script.js:
YOUTUBE_VIDEO_ID = "w6-zjCycdRs"
YOUTUBE_START_SECONDS = 2293

## Hành vi nhạc / video
Trong script.js:
RESUME_MUSIC_ON_VIDEO_END = false

- false: video kết thúc -> giữ im lặng; bấm "Quay lại thiệp & bật nhạc" mới phát lại.
- true: video kết thúc -> nhạc tự fade-in và tiếp tục từ vị trí trước đó.

Khi video PLAY:
- nhạc fade-out ~0.8 giây
- nhạc pause hoàn toàn

Khi video PAUSE:
- nếu nhạc trước đó đang phát, nhạc có thể bật lại.

## Thay nội dung
Trong index.html có các marker:
- EDIT PROGRAM NAME HERE
- EDIT THANK YOU MESSAGE HERE
- EDIT VIDEO HERE
- EDIT MUSIC HERE
- EDIT IMAGES HERE

Thay ảnh:
assets/images/trung-thu-1.svg
assets/images/trung-thu-2.svg
assets/images/trung-thu-3.svg

Bạn có thể đổi thành .jpg/.png/.webp, sau đó sửa src trong index.html.

## QR
QR hiện trỏ tới URL mẫu:
https://your-thank-you-card.com

KHÔNG in số lượng lớn với QR hiện tại.

Sau khi deploy website và có URL thật:
1. Mở file create_qr.py
2. Thay WEBSITE_URL bằng URL thật.
3. Chạy:
   python create_qr.py

Script sẽ tạo:
- qr-code.png
- thiep-qr-in-10x15cm-url-moi.png

Bạn cũng có thể nhờ ChatGPT tạo lại QR từ URL thật.

## Đưa website lên Internet miễn phí

### GitHub Pages
- Tạo repository mới.
- Upload toàn bộ file trong thư mục này.
- Settings -> Pages.
- Deploy from branch -> main / root.
- Nhận URL dạng https://username.github.io/ten-repo/

### Netlify
- Đăng nhập Netlify.
- Kéo-thả thư mục website vào trang deploy.
- Netlify sẽ tạo URL HTTPS.
- Có thể đổi tên site sau.

### Cloudflare Pages
- Kết nối repository GitHub.
- Chọn project tĩnh, không cần build command.
- Output directory là thư mục gốc.

Sau khi có URL thật, tạo lại QR MỘT LẦN.
Từ đó bạn có thể thay lời cảm ơn, ảnh, video, nhạc nhưng giữ nguyên URL,
nên QR đã in vẫn tiếp tục hoạt động.

## File thiệp in
- thiep-qr-in-10x15cm-300dpi.png: 10 x 15 cm, 300 DPI.
- thiep-qr-in-10x15cm.svg: vector, dễ chỉnh sửa.

## Lưu ý
Ảnh trong package là minh họa Trung Thu do bộ template tạo ra, không phải ảnh sự kiện thật.


# Timeline 2023–2026

Bản này đã thêm mục lục hành trình gồm 4 năm: 2023, 2024, 2025, 2026.

Mỗi năm có:
- Video clip
- Album ảnh
- Sao kê

## Thêm video cho từng năm
Mở `index.html`, tìm:
- `EDIT 2023 VIDEO`
- `EDIT 2024 VIDEO`
- `EDIT 2025 VIDEO`
- `EDIT 2026 VIDEO`

Ví dụ YouTube:
`https://www.youtube.com/watch?v=ABC123xyz`

Video ID là phần sau `v=`:
`ABC123xyz`

Điền:
`data-youtube-id="ABC123xyz"`

Nếu muốn bắt đầu tại giây 90:
`data-start="90"`

## Thêm sao kê
Đặt PDF vào:
`assets/statements/`

Ví dụ:
`assets/statements/sao-ke-2024.pdf`

Sau đó sửa nút tương ứng:
`href="assets/statements/sao-ke-2024.pdf" target="_blank"`

và XÓA:
`data-placeholder="true"`

## Nhạc nền
Bản timeline đã đặt loop:
- MUSIC_START = 90
- MUSIC_END = 150

Tức lặp từ 1 phút 30 giây đến 2 phút 30 giây.
Sửa trong `script.js` nếu muốn đổi.
