# Breakpad Dump 文件解析工具

本项目提供 `dump-helper.py` 脚本，用于快速解析 Breakpad 生成的 minidump 崩溃转储文件，将难以阅读的二进制 dump 文件转换为可读的堆栈跟踪信息。

## 工具原理

### 核心流程

```
┌──────────────┐    dump_syms            ┌──────────────┐
│  .so/.dll    │ ───────────────────────>│    .sym      │
│  动态库文件  │                         │   符号文件   │
└──────────────┘                         └──────────────┘
                                                │
                                                ▼
┌──────────────────┐  minidump_stackwalk  ┌──────────────┐
│  .dmp/.minidump  │ ────────────────────>│  .stack/.raw │
│  崩溃转储文件    │                      │  堆栈文件    │
└──────────────────┘                      └──────────────┘
```

### 工作步骤

1. **符号提取**：使用 `dump_syms` 工具从动态库文件（.so/.dll/.lib）中提取调试符号，生成 .sym 符号文件
2. **符号组织**：按照 Breakpad 标准目录结构（`模块名/ID/模块名.sym`）存储符号文件，便于快速查找
3. **堆栈解析**：使用 `minidump-stackwalk` 工具，结合符号文件解析 dump 文件，生成人类可读的堆栈跟踪

### 符号缓存机制

符号文件生成后会缓存在 `.sym` 目录下，按 `模块名/符号ID/模块名.sym` 结构组织。已解析过的符号会自动跳过，避免重复处理。

## 使用方法

### 基本用法

#### 方式一：命令行参数

```bash
# 处理单个文件
python dump-helper.py /path/to/libnative.so

# 处理多个文件
python dump-helper.py lib1.so lib2.so crash.dmp

# 处理整个目录（递归处理）
python dump-helper.py /path/to/crash_folder/

# 处理后自动关闭（适合脚本调用）
python dump-helper.py --auto-close crash.dmp
```

#### 方式二：交互式输入

直接运行脚本，按提示逐个输入文件路径：

```bash
python dump-helper.py
# Please input library or dump file(one by one):
# /path/to/libnative.so
# /path/to/crash.dmp
# (输入空行结束输入)
```

### 支持的文件类型

| 文件类型 | 后缀名 | 处理方式 |
|---------|-------|---------|
| 动态库（Linux/Android） | `.so` | 提取符号 |
| 动态库（Windows） | `.dll`, `.lib` | 提取符号 |
| 崩溃转储文件 | `.dmp`, `.minidump` | 解析堆栈 |

### 输出文件

| 输出文件 | 说明 |
|---------|------|
| `.stack` | 格式化的堆栈跟踪信息，包含函数名、源文件名、行号 |
| `.raw` | (--raw参数)原始 dump 信息，包含详细的寄存器状态、模块列表等 |

## 平台支持

| 平台 | 状态 |
|-----|------|
| Windows (x86_64) | ✅ 支持 |
| Linux (x86_64) | ✅ 支持 |
| macOS (x86_64) | ✅ 支持 |

## 工具优势

### 1. 一站式处理

传统方式需要分别调用 `dump_syms` 和 `minidump_stackwalk` 两个工具，手动管理符号文件路径。`dump-helper` 将两个工具整合，根据文件后缀自动识别处理流程：

```bash
# 传统方式（繁琐）
dump_syms libnative.so > libnative.so.sym
mkdir -p symbols/libnative.so/ABC123/
mv libnative.so.sym symbols/libnative.so/ABC123/
minidump_stackwalk crash.dmp symbols/ > crash.stack

# dump-helper 方式（简洁）
python dump-helper.py libnative.so crash.dmp
```

### 2. 智能符号管理

- **自动 ID 提取**：从符号文件首行自动提取 Build ID
- **标准目录结构**：按 Breakpad 标准组织符号文件，兼容其他工具
- **缓存机制**：已解析的符号自动跳过，避免重复工作
- **共享符号库**：所有 dump 文件共享同一个 `.sym` 符号目录

### 3. 批量处理能力

支持递归处理整个目录，一次性处理多个库文件和 dump 文件，适合批量分析场景。

### 4. 友好的输出格式

- **彩色终端输出**：使用颜色区分信息级别（错误/警告/信息）
- **格式化堆栈**：优化输出格式，文件名与行号紧密相连，便于 IDE 跳转
- **摘要预览**：自动显示前 20 行关键堆栈信息

### 5. 多种使用场景

| 场景 | 推荐方式 |
|-----|---------|
| 开发调试 | 拖拽文件到脚本 |
| CI/CD 集成 | 使用 `--auto-close` 参数 |
| 批量分析 | 传入目录路径 |
| 交互排查 | 运行脚本后逐个输入 |

## 目录结构

```
breadpad-dump-utils/
├── dump-helper.py           # 主脚本
├── third-party/
│   └── x86_64/
│       ├── win32/           # Windows 工具
│       │   ├── dump_syms.exe
│       │   └── minidump-stackwalk.exe
│       ├── linux/           # Linux 工具
│       │   ├── dump_syms-linux
│       │   └── minidump-stackwalk-linux
│       └── darwin/          # macOS 工具
│           ├── dump_syms-darwin
│           └── minidump-stackwalk-darwin
└── .sym/                    # 符号缓存目录（自动创建）
    └── libnative.so/
        └── ABC123DEF456/
            └── libnative.so.sym
```

## 第三方工具

### rust-minidump/minidump-stackwalk

- 仓库：https://github.com/rust-minidump/rust-minidump
- 版本：0.24.0 (2025-01-03)

### mozilla/dump_syms

- 仓库：https://github.com/mozilla/dump_syms
- 版本：2.3.4 (2024-09-06)

## 示例输出

```
#################### Stack Brief ####################
Thread 0 (crashed)
 #0 0x7fff12345678 in Foo::Bar() at src/foo.cpp:42
 #1 0x7fff23456789 in main at src/main.cpp:100
 #2 0x7fff34567890 in __libc_start_main
Crash reason:  SIGSEGV /0x0000000000
####################################################
```

## 常见问题

**Q: 符号文件已存在，如何重新生成？**

A: 手动删除 `.sym` 目录下对应的符号文件，然后重新运行脚本。

**Q: 解析结果显示内存地址而非函数名？**

A: 确保已提供对应的带调试符号的动态库文件（.so/.dll），且符号文件已正确生成。

**Q: 支持其他架构吗？**

A: 目前仅支持 x86_64 架构，如需其他架构请自行编译对应版本的工具。

## License

MIT License