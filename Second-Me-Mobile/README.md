# Second-Me Mobile

这是 Second-Me 的移动端应用，使用 **React Native** 和 **Expo Router** 构建。它提供了导入角色知识库和与 AI 角色对话的功能。

## 目录结构

```
Second-Me-Mobile/
├── app/                  # 页面路由 (Expo Router)
│   ├── _layout.js        # 全局导航布局
│   ├── index.js          # 首页
│   ├── chat.js           # 聊天页面
│   └── upload.js         # 角色导入页面
├── src/
│   └── services/
│       └── api.js        # API 客户端 (Axios)
├── package.json
└── app.json
```

## 快速开始

### 1. 安装依赖

确保你已安装 Node.js 和 npm。

```bash
cd Second-Me-Mobile
npm install
```

### 2. 启动开发服务器

```bash
# 启动 Expo 开发服务
npx expo start
```

*   按 `a` 在 Android 模拟器运行
*   按 `i` 在 iOS 模拟器运行
*   或使用 Expo Go App 扫描二维码在真机运行

### 3. 配置后端连接

默认情况下，应用会尝试连接本地后端：
*   **Android**: `http://10.0.2.2:8000/api` (模拟器映射宿主机 localhost)
*   **iOS**: `http://localhost:8000/api`

如果你的 `Second-Me-Lite` 后端运行在其他地址或局域网 IP，请修改 `src/services/api.js` 中的 `BASE_URL`。

## 功能说明

1.  **构造 AI 角色 (Construct AI Character)**:
    *   点击首页的 "Construct AI Character" 按钮。
    *   选择一个文本文件 (.txt) 或 Markdown 文件 (.md)。
    *   点击 "Start Ingestion" 上传并训练。
    *   后端会自动处理文件切片和向量化。

2.  **开始聊天 (Start Chatting)**:
    *   点击首页的 "Start Chatting" 按钮。
    *   发送消息，AI 将基于 RAG (检索增强生成) 回复你。
    *   聊天界面支持自动滚动和加载状态显示。

## 技术栈

*   React Native (Expo)
*   Expo Router (基于文件的路由)
*   Axios (网络请求)
*   Expo Document Picker (文件选择)
