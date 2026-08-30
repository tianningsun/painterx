# PainterX

`painterx` 是面向 macOS 和 Windows Adobe Illustrator 的无 Key 科研矢量绘图 skill。科研示意图默认按语义重绘，并用锚点质量门防止密集短线段；只有不规则纹理才使用本地 VTracer。运行时不联网、不上传图片、不需要 API Key。

## 环境

- macOS 12+ 或 Windows 10/11 x64
- Python 3.11–3.14
- Adobe Illustrator 2021（25.2+）至 2026
- macOS 使用 AppleScript；Windows 使用 PowerShell + Illustrator COM

## 安装

### 在 Codex 中直接安装

在有权访问本仓库的 Codex 中输入：

```text
$skill-installer 请从 https://github.com/tianningsun/painterx/tree/main/plugins/painterx/skills/painterx 安装 PainterX
```

安装完成后重启 Codex，并调用 `$painterx`。第一次使用会提示批准安装固定版本的免费本地依赖；不需要 API Key。以后运行不联网。

私有仓库要求用户已获邀并具有可用的 GitHub 登录或 Git 凭据。公开仓库无需 GitHub 凭据，但在上游许可问题解决前不要公开本仓库。

### 从发布 ZIP 安装

macOS：

```bash
./setup.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

安装后重启 Codex，调用 `$painterx`。播放时如 Illustrator 未启动则自动启动；如没有文档则新建一个空白文档。已有文档只追加独立图组，不清空原内容。

## 默认保护

- 不自动保存 Illustrator 文档。
- 不自动导出 PNG。
- 不关闭或退出 Illustrator。
- 不使用付费接口、免费额度或任何凭据。

## 诊断和打包

macOS 使用 `./doctor.sh` 和 `./build-release.sh`；Windows 使用 `.\doctor.ps1` 和 `.\build-release.ps1`。

打包后会在 `dist` 目录生成可分发的 ZIP 和 SHA-256 校验文件。接收方解压 ZIP 后进入同名目录：

macOS：

```bash
chmod +x *.sh
./setup.sh
```

Windows PowerShell：

```powershell
powershell -ExecutionPolicy Bypass -File .\setup.ps1
```

安装完成后重启 Codex，并在新任务中调用 `$painterx`。

## GitHub Release 发布

1. 新建名为 `painterx` 的 GitHub 仓库并上传本目录内容。
2. 运行构建脚本，生成 `dist/painterx-0.4.0-desktop.3.zip`。
3. 在 GitHub 仓库选择 **Releases → Draft a new release**，创建标签 `v0.4.0-desktop.3`。
4. 上传 ZIP 和对应的 `.sha256` 文件，说明支持的系统、Illustrator 版本、不需要 API Key，以及默认不保存、不导出。
5. 发布后把 Release 下载链接发给使用者；使用者按上一节执行安装脚本。

重要：本项目的部分实现思路来自当前没有明确开源许可证的上游仓库。获得原作者书面许可或完成独立重写并通过代码来源审查之前，只应私下测试，不应将当前 ZIP 公开发布或商业分发。

## 来源与边界

几何缓存与 Illustrator ExtendScript 绘图思路改编自 [yrui-cmd/cell-lct v0.2.1](https://github.com/yrui-cmd/cell-lct/tree/v0.2.1)。上游仓库当前未附带明确开源许可证；在获得作者许可前，建议仅用于个人测试和内部评估，不要公开再分发或商业化。
