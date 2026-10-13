# CHỈNH TIMELINE 2023–2026

## Mục lục
Thanh 2023 / 2024 / 2025 / 2026 là mục lục.
Bấm năm nào sẽ tự mở chương của năm đó và cuộn đến vị trí tương ứng.

## Mỗi năm có 3 nhóm
1. Video clip
2. Khoảnh khắc
3. Sao kê

## Video
Trong `index.html`, tìm:
`EDIT 2023 VIDEO`, `EDIT 2024 VIDEO`, ...

Điền YouTube Video ID vào:
`data-youtube-id=""`

Ví dụ URL:
`https://www.youtube.com/watch?v=w6-zjCycdRs`

thì:
`data-youtube-id="w6-zjCycdRs"`

## Ảnh
Tìm:
`EDIT 2023 IMAGES`, ...

Thay cả:
`src="..."`
và:
`data-full="..."`

bằng đường dẫn ảnh thật.

## Sao kê
Tìm:
`EDIT STATEMENT 2023`, ...

Ví dụ PDF local:
`href="assets/statements/sao-ke-2023.pdf" target="_blank"`

Sau đó xóa:
`data-placeholder="true"`

Hoặc dùng link Google Drive công khai trong `href`.

## Nhạc
Trong `script.js`:
`const MUSIC_START = 90;`
`const MUSIC_END = 150;`

Hiện tại nhạc lặp 1:30 → 2:30.

## Nút Hành trình
Nút nổi `☰ Hành trình` ở góc dưới giúp người xem quay lại mục lục bất cứ lúc nào.


## Giao diện pastel mới
- Màu chính: peach/pink/cream + mint green + vàng nhạt.
- Tiêu đề script dùng Google Font Dancing Script, có fallback hệ thống.
- Nội dung dùng Be Vietnam Pro; quote dùng Lora.
- Khi bấm Mở thiệp sẽ xuất hiện popup lời cảm ơn trước khi vào nội dung.
- Gallery của từng năm đã đổi sang scroll ngang, có scroll-snap trên mobile.

## Muốn thêm nhiều ảnh
Chỉ cần copy thêm một `<button class="gallery-card">...</button>` vào `.year-gallery`.
Gallery sẽ tự kéo ngang, không làm thay đổi layout content bên dưới.
