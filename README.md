# 房源数据清洗工具

本工具完全在本机运行，固定读取同目录下的四个 Excel 基础文件。双击 `start.bat`，浏览器会自动打开操作界面。

出于数据安全考虑，Git 仓库不包含楼盘字典和导入模板。首次运行前，请将以下文件放入项目根目录：`北京楼盘字典.xlsx`、`北京-单元楼盘字典.xlsx`、`售房数据导入模版.xlsx`、`租房数据导入模版 .xlsx`。

## 环境

- Windows 10/11
- Python 3.10 或更高版本
- `openpyxl`（执行 `pip install -r requirements.txt`）
- 读取旧版 `.xls` 时需安装 Microsoft Excel 或 LibreOffice；CSV、XLSX 不需要。

## 数据与规则

上传文件和生成文件均保存在本机 `data/`、`outputs/`，人工确认规则保存在 `data/rules.json`。每次新建任务都会重新检查并读取字典及所选模板。
