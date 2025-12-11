# Second-Me Flutter

这是 Second-Me 的移动端应用，使用 **Flutter** 构建，功能与 React Native 版本完全一致。

## 目录结构

```
Second-Me-Flutter/
├── lib/
│   ├── main.dart             # 应用入口
│   ├── src/
│   │   ├── models/           # 数据模型 (ChatMessage)
│   │   ├── screens/          # 页面 (Home, Chat, Upload)
│   │   └── services/         # 服务层 (Dio API Client)
├── pubspec.yaml              # 依赖管理
```

## 快速开始

### 1. 环境准备
确保你已安装 Flutter SDK。

```bash
cd Second-Me-Flutter
flutter pub get
```

### 2. 运行应用
连接 iOS/Android 模拟器或真机。

```bash
flutter run
```

### 3. 后端配置
默认情况下，应用会尝试连接本地后端：
*   **Android**: `http://10.0.2.2:8000/api`
*   **iOS**: `http://localhost:8000/api`

如果后端运行在其他地址，请修改 `lib/src/services/api_service.dart` 中的 `baseUrl`。

## 功能说明

与 React Native 版本一致：
1.  **Construct AI Character**: 选择 `.txt`/`.md` 文件上传，训练知识库。
2.  **Start Chatting**: 与基于 RAG 的 AI 角色进行实时对话。

## 技术栈对比 (Flutter vs React Native)

| 特性 | Flutter (本项目) | React Native (前一项目) |
| :--- | :--- | :--- |
| **语言** | Dart | JavaScript/TypeScript |
| **UI 渲染** | Skia 引擎自绘 (一致性强) | 原生组件映射 (更贴近原生) |
| **路由** | Navigator 2.0 / MaterialPageRoute | Expo Router (类 Web 路由) |
| **网络库** | Dio | Axios |
| **文件选择** | file_picker | expo-document-picker |
