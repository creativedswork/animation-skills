# 发布与安装

当前版本为 `0.1.0-dev.2`，三个 Skill 均为草案。工程提供本地打包与发布前检查；尚未指定远端平台，也未上传 Release。

## 预览包

在仓库根目录运行：

```bash
make preview
```

`dist/0.1.0-dev.2/` 包含三个独立 Skill ZIP、`manifest.json` 和 `SHA256SUMS`。清单记录预览属性、成熟度、每个包的源码文件指纹与 ZIP 指纹。相同版本目录不能覆盖；内容变化后提升预发布版本号再打包。

检查下载包完整性：

```bash
cd dist/0.1.0-dev.2
shasum -a 256 -c SHA256SUMS
```

完整性检查只能确认下载字节与清单一致，不证明动画能力或发行者身份。

## 正式版本

先完成 [工程约定](engineering.md#发布) 中的作品与迁移证据要求，再修改 `catalog.json` 的版本和成熟度。不要通过只修改标签绕过制作评价。当前草案执行正式检查会失败，这是预期行为。

在有完整输入与作品文件的环境执行：

```bash
python3 tools/project.py check --release
python3 -m unittest discover -s tests -v
python3 tools/project.py package --release
```

工具检查记录和文件完整性；作品的正确性、品味和人工帮助由评价者如实记录。源码中的草案说明也应随实际状态更新，然后重新获得对应版本的迁移证据。

检查修改并提交发布版本：

```bash
git status --short
git diff
git add .
git diff --cached --stat
```

确认暂存内容与发布包对应后创建提交及标签：

```bash
release_version=$(python3 -c 'import json; print(json.load(open("catalog.json"))["version"])')
git commit -m "Release v${release_version}"
git tag -a "v${release_version}" -m "Animation Skills ${release_version}"
```

## 上传远端

先由维护者选择仓库、可见范围和分发条款，并配置 `origin`。本工程不选择托管平台。已有 Git 远端后，可以推送当前发布提交和标签：

```bash
git push origin main "v${release_version}"
```

若使用 GitHub，并已安装、登录 `gh`，可在同一终端上传：

```bash
gh release create "v${release_version}" \
  dist/"${release_version}"/*.zip \
  dist/"${release_version}"/manifest.json \
  dist/"${release_version}"/SHA256SUMS \
  --verify-tag --title "Animation Skills ${release_version}" --generate-notes
```

本地生成 ZIP、创建 Git 标签和远端发布是三个不同状态。上传后读取 Release，确认版本、附件和校验文件，再报告已发布。预览包若分享，应显式标记为预发布。

## 安装单个 Skill

将 ZIP 解压到临时目录，核对内容后，把其中的 `<skill-name>/` 目录复制到目标产品的 Skill 目录：

| 范围 | TRAE 路径 |
| --- | --- |
| 项目级 | `<project>/.trae/skills/` |
| CN 用户级 | `~/.trae-cn/skills/` |
| 国际版用户级 | `~/.trae/skills/` |

先检查同名目录，保留本地修改再决定更新。安装后在新会话中确认 Skill 被发现；本地结构验证不能替代实际运行时发现验证。Meshy 与 Blender 的安装、MCP 配置和服务授权由使用环境提供，不包含在 ZIP 中。
