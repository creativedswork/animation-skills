# 查看器验证

拖放检查在 Chrome 中执行，使用 Chromium 的拖放接口从磁盘读取文件，验证浏览器生成的文件拖放事件、Three.js 加载和动作播放。测试需要一个包含可见动作、贴图和缓冲数据内嵌的 GLB。

先运行 `npm ci` 和 `make viewer`。另开终端，在仓库根目录执行：

```bash
node tests/viewer-drop.mjs \
  /path/to/playwright/index.mjs \
  /path/to/animated.glb \
  http://127.0.0.1:8765
```

前两个参数分别替换为本机已安装的 Playwright 入口和动画文件。脚本使用系统 Chrome；Playwright 仅用于开发验证，不是查看器的运行依赖。没有 Playwright 时，可在独立工具目录通过 `npm install playwright` 安装，然后使用该目录的 `node_modules/playwright/index.mjs`。

通过后会输出浏览器版本、片段时长和通过的检查项，并在 `.artifacts/viewer-drop/` 保存结果和截图：

- 拖入高亮、跨视图子元素移动、取消拖放。
- A、B 分别加载 GLB，播放进度推进且渲染姿势改变。
- 两个视图独立选择动作，原有文件选择按钮继续可用。
- 格式错误、损坏文件和多文件拖入显示可恢复错误。
- 错误后重新拖入成功，视图外拖放不打开文件或离开页面。
- 本地文件加载不发送上传请求，页面无未捕获异常。

发布前还应在不含 `.artifacts/` 的新克隆目录启动服务，使用相同命令验证“缺少历史素材 → 拖入本地 GLB → 播放”路径。记录文件来自测试环境，不提交 Git。

人工检查时，从 Finder 或文件管理器拖入 GLB，确认目标视图出现提示；再检查侧面、慢放、旋转和缩放。自动检查可验证加载和播放行为，动作是否自然仍需观看评价。
