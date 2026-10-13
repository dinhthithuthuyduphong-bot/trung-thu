TRUNG THU CHO EM — FINAL ONE-PAGE

FLOW
1. Mở website:
   - Thiệp pastel 2 cánh ở giữa màn hình.
   - Responsive cho mobile / cửa sổ nhỏ.

2. Bấm "Mở thiệp":
   - Hai cánh mở sang trái/phải.
   - Popup lời cảm ơn hiện.
   - Nhạc LỜI CẢM ƠN phát.

3. Popup:
   - CHỈ 1 TRANG.
   - Nội dung theo phong cách bản CAROUSEL.
   - Nếu màn hình thấp, phần popup tự cuộn dọc.

4. Bấm "Mở hành trình kỷ niệm":
   - Nhạc cảm ơn fade-out.
   - Nhạc KHÔNG LỜI hành trình fade-in.
   - Vào timeline 2023–2026.
   - Auto-scroll chậm; chạm/click/wheel thì dừng.

5. Video:
   - Video phát -> nhạc hành trình dừng.
   - Pause video -> nhạc hành trình có thể quay lại.
   - Kết thúc video: mặc định giữ im lặng.

6. Cuối trang:
   - "Đọc lại lời cảm ơn ↑"
   - Dừng nhạc hành trình.
   - Mở lại popup 1 trang.
   - Nhạc cảm ơn phát lại.

THAY NHẠC
assets/music/thank-you.mp3
  -> bài nhạc dành cho popup lời cảm ơn.

assets/music/journey-instrumental.mp3
  -> bản không lời cho phần kỷ niệm.

Nếu 2 MP3 chưa tồn tại, website tự dùng WAV fallback có sẵn.

ĐOẠN NHẠC CẢM ƠN HIỆN TẠI
script.js:
THANKYOU_MUSIC_START = 71
THANKYOU_MUSIC_END   = 109

Nếu bài mới cần chạy từ đầu:
THANKYOU_MUSIC_START = 0
và đặt THANKYOU_MUSIC_END theo độ dài mong muốn.

UPLOAD NETLIFY
Giải nén ZIP -> kéo nguyên thư mục lên Netlify Drop.
