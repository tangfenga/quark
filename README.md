# Quark CLI

这是一个功能强大的命令行工具，用于与夸克网盘 API 交互，帮助您自动解压、整理和清理文件。

该工具提供了一个可重用的 `QuarkAPI` 库，并附带一个简单易用的命令行界面（CLI），让您可以轻松管理夸克网盘中的压缩文件。

## ✨ 功能

- **自动解压**：支持解压 `.zip`, `.rar`, `.7z`, `.tar`, `.gz` 等多种格式的压缩文件。
- **智能整理**：解压后，自动将文件从临时文件夹移动到目标目录。
- **自动清理**：移动文件后，自动删除遗留的空文件夹和原始压缩包（可选）。
- **路径解析**：支持通过网盘路径（如 `/MyFolder/SubFolder`）获取内部 FID。
- **失败重试**：对解压、整理和清理过程中失败的任务进行自动重试。
- **配置文件**：通过简单的 `config.json` 文件管理 `cookie` 和目标目录。
- **调试模式**：提供 `--debug` 标志，用于输出详细的 API 请求和响应信息。

## 🚀 安装

本项目使用 `uv` 进行包管理。请按照以下步骤进行安装：

1.  **克隆或下载项目**：
    将项目文件保存到本地。

2.  **安装依赖**：
    在项目根目录（`quark` 目录）下，运行以下命令以安装项目及其依赖项：

    ```bash
    uv pip install -e .
    ```
    这将在可编辑模式下安装 `quark-cli`，方便您进行后续的开发和修改。

## ⚙️ 配置

在首次运行 `quark-cli` 之前，您需要进行配置。

### 自动配置（推荐）

直接运行 `quark-cli`，程序会自动检测 `config.json` 文件是否存在。如果不存在，它将引导您：

1.  输入您的夸克网盘 `cookie`。
2.  输入您要操作的目标目录（默认为根目录 `/`）。

配置信息将自动保存到 `config.json` 文件中。

### 手动配置

您也可以手动在项目根目录创建一个 `config.json` 文件，并填入以下内容：

```json
{
  "cookie": "在此处粘贴您的夸克网盘Cookie",
  "target_directory": "/"
}
```

- `cookie`: 您的夸克网盘登录凭证。
- `target_directory`: 您希望执行解压和整理操作的网盘路径（例如 `/MyEbooks/Pending`）。

## 💡 用法

安装并配置完成后，您可以直接在终端中运行 `quark-cli`。

### 基本用法

```bash
quark-cli
```

运行后，程序将：
1.  读取 `config.json` 获取 `cookie` 和目标目录。
2.  扫描目标目录下的所有压缩文件。
3.  询问您是否要在任务成功后删除原始压缩包。
4.  开始执行解压、整理和清理任务。

### 命令行参数

- `--config <PATH>`: 指定配置文件的路径（默认为 `config.json`）。
  ```bash
  quark-cli --config /path/to/your/config.json
  ```

- `--debug`: 启用调试模式，打印详细的 API 请求和响应日志。
  ```bash
  quark-cli --debug
  ```

## 📚 作为库使用

除了作为命令行工具，您还可以将 `QuarkAPI` 类导入到您自己的 Python 脚本中，以实现更灵活的自动化操作。

### 示例

以下是一个简单的示例，演示如何使用 `QuarkAPI` 库来获取指定目录下的文件列表：

```python
from quark_cli.api import QuarkAPI
import json

# 从配置文件加载 cookie
with open('config.json', 'r') as f:
    config = json.load(f)
    cookie = config.get('cookie')

if not cookie:
    raise ValueError("Cookie not found in config.json")

# 初始化 API
api = QuarkAPI(cookie=cookie, debug=True)

try:
    # 获取根目录的 FID
    root_fid = api.get_fid_by_path('/')
    
    # 获取根目录下的所有文件和文件夹
    items = api.get_files_by_pid(root_fid)
    
    print("根目录下的项目：")
    for item in items:
        item_type = "文件夹" if item.get("dir") else "文件"
        print(f"- {item['file_name']} ({item_type})")

except Exception as e:
    print(f"发生错误: {e}")

```
