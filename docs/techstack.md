# Tech Stack & Server Sizing cho NLSQL Production

Dựa theo kiến trúc hệ thống hiện tại của dự án NLSQL và các luồng xử lý Agentic, dưới đây là bảng Tech Stack chi tiết trải dài thêm các frameworks đang được sử dụng ở tầng ứng dụng và ước lượng cấu hình hệ thống (Server Sizing) cần thiết để triển khai Production.

Cấu hình này giả định một lượng tải trung bình - khá và bộ dữ liệu đánh chỉ mục Vector lớn (ví dụ: bài toán search 500k SKUs).

## 1. Bảng cấu hình Tech Stack và Tài nguyên

| STT | Thành phần | Công cụ | CPU | RAM | Storage |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 1 | Web Frontend (UI & Dashboard) | **Next.js (Node.js React UI)** | 2–4 vCPU | 4–8 GB | 20 GB |
| 2 | Backend API & Workflow Engine | **Python (FastAPI, LangChain, LangGraph)** | 4–8 vCPU | 8–16 GB | 50 GB |
| 3 | Metadata & App State Database | **PostgreSQL 16** | 4–8 vCPU | 8–16 GB | 100–200 GB |
| 4 | Vector Database (Semantic Search)| **Qdrant** | 8–16 vCPU | 16–32 GB | 200–500 GB* |
| 5 | Cache & Pub/Sub (Cho cơ chế Streaming) | **Redis** | 2 vCPU | 4–8 GB | 20 GB |
| 6 | Load Balancer / Reverse Proxy | **Nginx / Traefik** | 2 vCPU | 2–4 GB | 20 GB |

*\* Phụ thuộc vào tổng kích thước và chunking size của document bạn định vector hóa. Qdrant rất ưu tiên **RAM** lớn để lưu trữ HNSW graph hoàn toàn trên memory, qua đó đảm bảo độ trễ truy vấn vector luôn ở mức thấp nhất.*

---

## 2. Các phương án thực thi triển khai (Deployment Strategy)

### Phương án 1: Single Server / Standalone (Dành cho MVP Production / Tải vừa)
Triển khai tập trung toàn bộ các dịch vụ trên nền tảng 1 máy chủ vật lý, hoặc 1 máy ảo (Cloud VM). Phù hợp để làm chốt chặn ban đầu.
- **Cấu hình tổng khuyến nghị:** `16 - 32 vCPU` | `32 - 64 GB RAM` | `1 TB SSD/NVMe`.
- **Triển khai:** Sử dụng trực tiếp `docker-compose.yml` để quản lý vòng đời của các container services. Dùng Nginx làm Reverse Proxy để điều hướng request tới Next.js hoặc FastAPI, đồng thời cấu hình chứng chỉ SSL/TLS. Lưu trữ Volume của Qdrant và Postgres thẳng trên ổ đĩa SSD cục bộ.

### Phương án 2: High Availability / Phân mảnh (Scale khi tải ứng dụng tăng mạnh)
Khi lượng người dùng truy vấn Agentic workflow đồng thời qua LangGraph/LangChain cao, bạn cần kiến trúc phân tán:
- **Tách riêng Storage & DB:** Migrate PostgreSQL và đặc biệt là Qdrant sang cụm máy chủ biệt lập (hoặc tận dụng các Managed Database Services của Cloud Provider). Hạ tầng Storage cần yêu cầu IOPS cực tốt vì việc ghi log lịch sử hội thoại liên tục cho state-machine LangGraph và việc Update Index trên Qdrant ngốn khá nhiều I/O.
- **Scale ngang (Horizontal Scaling) Backend API / Queue:** Hệ thống Workflow (Agent LLM Callers với API) thường bị phụ thuộc vào độ trễ mạng khi gọi LLM (OpenAI API) và cần chạy tác vụ nền thường xuyên qua celery/Redis workers. Bạn có thể sử dụng Kubernetes (K8s) hoặc Docker Swarm để cấu hình auto-scaling cho các container FastAPI và Worker.
- **Tách Instance cho Cache/Pubsub:** Redis nên được cô lập và có HA (High Availability) nhằm đảm bảo hệ thống SSE Streaming Realtime của Agent không bị gián đoạn hay mất gói tin khi hệ thống bị quá tải tạm thời.
