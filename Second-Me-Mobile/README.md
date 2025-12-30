# Second-Me Mobile

这是 Second-Me 的移动端应用，使用 **React Native** 和 **Expo Router** 构建。它提供了导入角色知识库和与 AI 角色对话的功能。

## 目录结构

```
Second-Me-Mobile/
├── app/                  # 页面路由 (Expo Router)
│   ├── _layout.js        # 全局导航布局
│   ├── index.js          # 入口页面（重定向到欢迎页）
│   ├── welcome.js        # 欢迎页面
│   ├── name-input.js     # 名字输入页面
│   ├── info-collection.js # 信息采集页面（第三个界面）
│   ├── home.js           # 主界面（包含上传文件和聊天窗两个功能块）
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

### 3. Android 原生构建配置

如果使用 `npx expo run:android` 进行原生构建，需要配置 Android SDK 路径：

**方法一：创建 local.properties 文件（推荐）**

在 `android/local.properties` 文件中设置 SDK 路径（该文件已自动生成，通常不需要手动创建）：

```properties
sdk.dir=D\:\\Users\\你的用户名\\AppData\\Local\\Android\\Sdk
```

**方法二：设置环境变量**

设置 `ANDROID_HOME` 环境变量指向 Android SDK 目录：
- Windows: `%LOCALAPPDATA%\Android\Sdk`
- macOS/Linux: `~/Library/Android/sdk` 或 `$HOME/Android/Sdk`

**常见问题：**

如果遇到 "SDK location not found" 错误，请检查：
1. 是否已安装 Android Studio 和 Android SDK
2. `local.properties` 文件中的路径是否正确（Windows 路径需要使用双反斜杠 `\\`）
3. 路径中是否包含中文字符（建议避免）

### 4. 配置后端连接

默认情况下，应用会尝试连接本地后端：
*   **Android 模拟器**: `http://10.0.2.2:8001/api` (模拟器映射宿主机的 localhost)
*   **iOS 模拟器**: `http://localhost:8001/api`

**注意**: 
- 前端默认连接本地后端（`localhost:8001`），后端运行在 `0.0.0.0:8001` 允许其他电脑访问
- 如需连接其他电脑的后端，请修改 `src/services/api.js` 中的 `BASE_URL` 为对应的 IP 地址（例如：`http://192.168.1.100:8001/api`）
- 如需在真机上测试并连接本地后端，需要将 `BASE_URL` 配置为你电脑的局域网 IP 地址

如果你的 `Second-Me-Lite` 后端运行在其他地址或端口，请修改 `src/services/api.js` 中的 `BASE_URL`。

## 功能说明

### 应用流程

1. **欢迎页面**: 应用启动后进入欢迎页面，展示"第二自我"的介绍
2. **名字输入**: 用户输入自己的名字
   - 采用现代化的渐变背景和动画效果
   - 包含精美的图标设计和交互反馈
   - 输入框支持聚焦动画和视觉反馈
   - 按钮具有渐变效果和阴影，提供良好的视觉层次
3. **信息采集**: 与AI对话，采集用户信息来塑造"第二自我"
   - 支持文本输入和语音输入（语音功能待实现）
   - 右上角有"跳过"按钮，可跳过信息采集直接进入主界面
4. **主界面**: 包含两个功能块
   - **上传文件**: 导入角色知识库
   - **聊天窗**: 与AI角色对话

### 主要功能

1.  **上传文件 (Upload Character)**:
    *   在主界面点击"上传文件"块。
    *   选择一个文本文件 (.txt) 或 Markdown 文件 (.md)。
    *   点击 "Start Ingestion" 上传并训练。
    *   后端会自动处理文件切片和向量化。

2.  **开始聊天 (Chat with AI)**:
    *   在主界面点击"聊天窗"块。
    *   发送消息，AI 将基于 RAG (检索增强生成) 回复你。
    *   聊天界面支持自动滚动和加载状态显示。

## 设计风格

应用采用**简洁**的设计风格，配合**浅粉色混浅蓝色**的配色方案：
*   **设计理念**: 简洁、清爽、专注于内容
*   **主背景渐变**: 从浅粉色 (#FFE5F0) 过渡到浅蓝色 (#E5F0FF, #D6E8FF)
*   **按钮样式**: 简洁的白色背景按钮，粉色文字 (#FF6B9D)
*   **输入框**: 半透明白色背景，简洁边框
*   **去除装饰**: 无复杂动画、光晕、装饰性元素，保持界面简洁

## 技术栈

*   React Native (Expo)
*   Expo Router (基于文件的路由)
*   Axios (网络请求)
*   Expo Document Picker (文件选择)
*   Expo Linear Gradient (渐变背景)
