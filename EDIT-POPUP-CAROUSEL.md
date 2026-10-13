# CHỈNH POPUP VÀ ẢNH CUỘN NGANG

## Popup mở thiệp
Nội dung nằm trong `index.html`.

Tìm:
`<!-- OPEN CARD POPUP: short emotional opener, not a duplicate thank-you message -->`

Các phần dễ sửa:
- `popup-label`: TRUNG THU CHO EM
- `popup-year`: 2023 — 2026
- `popup-title`: tiêu đề lớn
- `popup-message`: thông điệp ngắn
- `popup-emphasis`: câu nhấn
- `popup-continue`: chữ trên nút

Popup được cố ý viết ngắn để KHÔNG trùng với phần "LỜI CẢM ƠN" bên dưới.

## Ảnh cuộn ngang
Không cần thay JavaScript khi thêm ảnh.

Trong `index.html`, vào đúng năm và copy thêm một thẻ:

```html
<button class="gallery-card"
        data-full="assets/images/2026/04.jpg"
        type="button">
  <img src="assets/images/2026/04.jpg"
       alt="Khoảnh khắc năm 2026"
       loading="lazy">
  <span>Khoảnh khắc 04</span>
</button>
```

Gallery tự:
- vuốt ngang bằng tay trên điện thoại;
- có nút → để đi sang ảnh kế;
- có hiệu ứng snap từng ảnh;
- hé một phần ảnh kế bên để gợi ý còn ảnh;
- có dòng "Vuốt để xem thêm →";
- kéo bằng chuột trên desktop.

## Màu / font popup
Nằm trong `style.css`.
Tìm:
`WOW POPUP + HORIZONTAL PHOTO CAROUSEL`
