def export_md(text: str) -> bytes:
    return text.encode("utf-8")


def export_pdf(text: str) -> bytes:
    import markdown as md_lib
    from weasyprint import HTML

    html_body = md_lib.markdown(text, extensions=["tables", "fenced_code"])
    html = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: "Noto Sans CJK SC", "Noto Sans", sans-serif; margin: 2cm; font-size: 11pt; line-height: 1.6; }}
  h1, h2, h3 {{ color: #1a1a2e; }}
  h1 {{ font-size: 18pt; border-bottom: 2px solid #1a1a2e; padding-bottom: 4px; }}
  h2 {{ font-size: 14pt; border-bottom: 1px solid #ccc; padding-bottom: 2px; }}
  ul {{ padding-left: 1.2em; }}
  code {{ background: #f4f4f4; padding: 0 3px; border-radius: 3px; }}
  pre {{ background: #f4f4f4; padding: 10px; border-radius: 4px; overflow-x: auto; }}
</style>
</head>
<body>{html_body}</body>
</html>"""
    return HTML(string=html).write_pdf()
