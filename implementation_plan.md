# Tối ưu hóa tốc độ với Đa luồng (Multi-threading)

Bạn nói rất đúng, nếu chạy từng câu một với tốc độ 30-40 giây/câu thì 1000 câu sẽ tốn khoảng 10-12 tiếng. Quá lâu!

Để giải quyết triệt để vấn đề này, tôi đề xuất **nâng cấp un_batch_inference.py\ để chạy song song nhiều câu cùng lúc (Multi-threading)**. Với cách này, chúng ta có thể gọi API cùng lúc cho 5-10 câu hỏi, giảm thời gian chạy xuống chỉ còn 1-2 tiếng.

## User Review Required

> [!IMPORTANT]
> - Việc chạy song song (ví dụ 5 luồng) sẽ tiêu tốn quota/rate limit của API nhanh hơn (do gửi 5 request cùng lúc).
> - Nếu bạn đang dùng API key của OpenRouter/Gemini, thông thường họ cho phép chạy song song khá thoải mái, nhưng nếu gặp lỗi \Rate Limit (429)\ thì chúng ta có thể giảm số luồng xuống.

## Proposed Changes

### [Tối ưu Code Inference]

#### [MODIFY] [run_batch_inference.py](file:///c:/Users/Minh/Desktop/My-Project/AI-Agent-Financial-DataAnalyst-Assistant/run_batch_inference.py)
- Thêm tham số cờ \--workers\ vào dòng lệnh (mặc định là 1, nhưng có thể truyền \--workers 5\).
- Đóng gói toàn bộ logic xử lý 1 câu hỏi thành một hàm \process_question()\.
- Sử dụng \concurrent.futures.ThreadPoolExecutor\ để chạy song song.
- Thêm \	hreading.Lock()\ vào phần ghi file \submission.json\ để đảm bảo không bị lỗi mất dữ liệu khi nhiều luồng cùng ghi đè lên ổ cứng.
- Tích hợp thanh tiến trình \	qdm\ mượt mà với đa luồng.

## Verification Plan
1. Tôi sẽ tắt lệnh bạn đang chạy hiện tại.
2. Sửa code un_batch_inference.py\.
3. Chạy lại với cờ \--workers 5\ để bạn xem tốc độ tăng lên gấp 5 lần như thế nào!
