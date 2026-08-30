"""导出 FastAPI OpenAPI 文档，供前端 Worma 生成器使用。"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from .app import app


def main() -> None:
    parser = argparse.ArgumentParser(description="导出 FastAPI OpenAPI JSON 文档")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("backend/openapi.json"),
        help="输出文件路径（相对于当前工作目录）",
    )
    args = parser.parse_args()
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(app.openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI 文档已导出到 {output}")


if __name__ == "__main__":
    main()
