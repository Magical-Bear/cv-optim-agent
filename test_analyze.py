"""Quick end-to-end test: upload PDF → analyze → confirm → export"""
import json
import sys
import requests

BASE = "http://localhost:8000"

# ── 1. Upload ──────────────────────────────────────────────────────────────
pdf_path = "/Users/magicalbear/projects/interview/tengyun/cv-optim-agent/test_cv/王贝尔简历2.pdf"
print("=== 1. Upload ===")
with open(pdf_path, "rb") as f:
    r = requests.post(f"{BASE}/api/upload", files={"file": ("resume.pdf", f, "application/pdf")})
r.raise_for_status()
upload_data = r.json()
sid = upload_data["session_id"]
resume_text = upload_data["text"]
print(f"session_id: {sid}")
print(f"resume text length: {len(resume_text)} chars")

# ── 2. Analyze ─────────────────────────────────────────────────────────────
JD = """岗位：大模型应用工程师
职责：
1. 基于LangChain/LangGraph构建企业级Multi-Agent系统，设计Agent编排流程
2. 使用RAG技术构建知识库问答系统，优化检索精度与生成质量
3. 负责大模型微调（SFT/RLHF），使用DeepSpeed/FSDP进行分布式训练
4. 开发FastAPI后端服务，对接vLLM推理框架，保证高并发稳定性
5. 参与MCP协议工具开发，构建AI与业务系统集成方案
要求：
- 熟练Python，掌握FastAPI异步编程
- 熟悉LangChain/LangGraph，有Multi-Agent项目经验
- 了解RAG系统设计，熟悉向量数据库（Milvus/Chroma/Qdrant）
- 有大模型微调经验（LoRA/QLoRA），熟悉HuggingFace生态
- 加分项：有vLLM/TGI部署经验，熟悉MCP协议"""

print("\n=== 2. Analyze (LangGraph running...) ===")
r = requests.post(
    f"{BASE}/api/analyze",
    json={"session_id": sid, "resume_text": resume_text, "jd_text": JD},
    timeout=120,
)
r.raise_for_status()
analyze_data = r.json()
print(f"Match score: {analyze_data['match_report']['score']}")
print(f"Highlights: {analyze_data['match_report']['highlights'][:3]}")
print(f"Gaps: {analyze_data['match_report']['gaps'][:3]}")
print(f"Suggestions count: {len(analyze_data['suggestions'])}")
for s in analyze_data["suggestions"][:3]:
    print(f"  [{s['priority']}] {s['id']}: {s['suggested_text'][:60]}...")

# ── 3. Confirm (select first 2 suggestions) ────────────────────────────────
suggestion_ids = [s["id"] for s in analyze_data["suggestions"][:2]]
print(f"\n=== 3. Confirm (selecting {suggestion_ids}) ===")
r = requests.post(
    f"{BASE}/api/confirm",
    json={
        "session_id": sid,
        "selected_suggestions": suggestion_ids,
        "edited_suggestions": [],
        "extra_note": "保持简洁专业风格，突出AI工程落地能力",
    },
    timeout=120,
)
r.raise_for_status()
confirm_data = r.json()
optimized = confirm_data["optimized_resume"]
print(f"Optimized resume length: {len(optimized)} chars")
print("--- Preview (first 300 chars) ---")
print(optimized[:300])

# ── 4. Export MD ───────────────────────────────────────────────────────────
print("\n=== 4. Export MD ===")
r = requests.get(f"{BASE}/api/export/{sid}?format=md")
r.raise_for_status()
with open("/tmp/resume_optimized.md", "wb") as f:
    f.write(r.content)
print(f"MD saved to /tmp/resume_optimized.md ({len(r.content)} bytes)")

print("\n✓ All steps passed.")
