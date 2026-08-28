# 11 - MultiHiertt Benchmark & Hierarchical Tree Schema Encoding

Tài liệu này phân tích chuyên sâu các giới hạn của mô hình **Text-to-Pandas** khi đối mặt với Bảng biểu tài chính phân cấp đa tầng (Hierarchical Financial Tables), trích xuất từ nghiên cứu **MultiHiertt Benchmark (Zhao et al., ACL 2022)** và đề xuất giải pháp kỹ thuật nâng cấp kiến trúc cho hệ thống.

---

## 📌 1. Giới hạn của Text-to-Pandas với Bảng Biểu Tài Chính Thực Tế

### Giả định Ngây thơ (Flat Table 2D) vs. Thực tế Báo cáo Tài chính (10-K / BCTC)

| Giả định Flat Table | Thực tế BCTC Doanh nghiệp (10-K / 10-Q) |
| :--- | :--- |
| Bảng phẳng 2D chuẩn kích thước $M \times N$. | **Multi-level Hierarchical Headers/Rows**: Tiêu đề lồng ghép 3–4 cấp (Năm > Quý > Phân khúc). |
| Mỗi cột/hàng chỉ có 1 header duy nhất. | **Merged Cells / Spans**: Ô gộp, xuất hiện các dòng tổng con (Subtotals) cắt ngang bảng. |
| Các hàng hoàn toàn độc lập. | **Quan hệ Cây (Parent-Child)**: Hàng con kế thừa ngữ cảnh hàng mẹ (ví dụ: *Tài sản ngắn hạn > Tiền và tương đương tiền*). |
| Văn bản và Bảng biểu tách rời. | **Cross-table & Footnote Linking**: Cần kết hợp số liệu từ nhiều bảng và các chú thích chân trang (Footnotes / Thuyết minh BCTC). |

---

## 📊 2. Phân Tích MultiHiertt Benchmark (Zhao et al., ACL 2022)

### Đặc điểm Benchmark
- Trích xuất từ Báo cáo Thường niên thực tế của các công ty niêm yết.
- Đòi hỏi **Multi-hop Reasoning** phức tạp: Duyệt cây bảng 1, đối chiếu điều kiện bảng 2 và kết hợp tỷ lệ % trong văn bản thuyết minh.
- Yêu cầu **Hierarchical Path Matching** và **Cross-Evidence Aggregation** (hơn 70% câu hỏi đòi hỏi từ 3 số liệu rải rác trở lên).

### Kết quả Thực nghiệm trên MultiHiertt Benchmark

| Mô hình (Model) | Tập Dev (EM %) | Tập Dev (F1 %) | Tập Test (EM %) | Tập Test (F1 %) |
| :--- | :---: | :---: | :---: | :---: |
| Longformer + Reasoning | 2.71 | 6.93 | 2.86 | 6.23 |
| Facts Retrieving + TAPAS | 8.94 | 10.70 | 7.67 | 10.04 |
| Facts Retrieving + NumNet | 10.32 | 12.59 | 10.77 | 12.02 |
| TAGOP (RoBERTa-large) | 19.16 | 21.08 | 17.81 | 19.35 |
| Facts Retrieving + Seq2Prog | 26.19 | 28.74 | 24.58 | 26.30 |
| FinQANet (RoBERTa-large) | 32.41 | 35.37 | 31.72 | 33.60 |
| MT2Net (RoBERTa-large) **(SOTA)** | **37.05** | **39.96** | **36.22** | **38.43** |
| **Chuyên gia con người (Human Expert)** | **—** | **—** | **83.12** | **87.03** |

### Key Takeaways (Rút ra từ Thực nghiệm):
1. **Chương trình biểu diễn (Program/Seq2Prog/PoT) là chìa khóa bứt phá**: Tăng từ <10% (TAPAS/Longformer) lên 36.22% EM (MT2Net/FinQANet).
2. **Khoảng cách với con người còn rất lớn (46.9%)**: Nguyên nhân chính là do sự thất bại trong việc khớp đúng đường dẫn phân cấp (Hierarchical Path Matching).

---

## 🛠️ 3. Giải pháp Kiến trúc: Coordinate & Header Path Linearization

Để triệt tiêu lỗi mất ngữ cảnh phân cấp khi đưa ô dữ liệu vào LLM, hệ thống áp dụng kỹ thuật **Coordinate & Header Path Linearization**:

Biểu diễn mỗi ô dữ liệu $c_{i,j}$ dưới dạng đường dẫn tọa độ phẳng mở rộng đầy đủ:
$$c_{i,j} = \left( \text{RowPath}(i), \text{ColPath}(j), \text{Value} \right)$$

### Ví dụ Thực tế:
Một ô dữ liệu có giá trị `68.4%` trong BCTC được mã hóa thành:
```text
[RowPath: Kết quả kinh doanh > Phân khúc Cloud > Lợi nhuận gộp | ColPath: Năm 2023 > Quý 4 | Value: 68.4%]
```

### Lợi ích cho PoT Strategy:
- LLM (`Qwen2.5-Coder`) không còn phải tự đoán vị trí dòng/cột lồng ghép.
- Phá vỡ sự phức tạp của bảng 2D gộp ô, chuyển thành cấu trúc các đường dẫn đại số độc lập: `NUM_0: (RowPath=..., ColPath=..., Value=...)`.
