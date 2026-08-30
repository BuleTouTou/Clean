import { defineConfig } from "wormajs";
import { alova } from "wormajs/plugin";

/**
 * 从 FastAPI 导出的 OpenAPI 文档生成 Alova API 调用代码。
 *
 * `bun run worma:gen` 会先刷新 ../backend/openapi.json，再执行 worma gen。
 * 生成内容位于 src/generated/，业务代码不要直接修改该目录中的生成文件。
 */
export default defineConfig({
  generator: [
    {
      input: "../backend/openapi.json",
      output: "src/generated",
      serverName: "房源数据清洗服务",
      docComment: true,
      plugins: [alova()],
    },
  ],
});
