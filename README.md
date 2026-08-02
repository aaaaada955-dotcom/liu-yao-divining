# 六爻游戏

## 让 AI 解读正常工作（通义千问）

1. 在自己的电脑运行时：复制 `.env.example` 为 `.env`，再填写阿里云百炼 API Key 和 OpenAI 兼容地址。
2. 部署到 Streamlit Cloud 时：在应用的 **Settings → Secrets** 中新增：

```toml
DASHSCOPE_API_KEY = "你的百炼 API Key"
DASHSCOPE_BASE_URL = "你的百炼 OpenAI 兼容地址"
```

不要把真实 Key 写进 `main.py`，也不要上传到 GitHub。

# demo

![demo1](./doc/demo1.png)
![demo2](./doc/demo2.png)
