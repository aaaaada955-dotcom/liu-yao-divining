# 六爻游戏

## 让 AI 解读正常工作

1. 在自己的电脑运行时：复制 `.env.example` 为 `.env`，再在等号后填入自己的 OpenAI API Key。
2. 部署到 Streamlit Cloud 时：在应用的 **Settings → Secrets** 中新增一行：

```toml
OPENAI_API_KEY = "你的 Key"
```

不要把真实 Key 写进 `main.py`，也不要上传到 GitHub。

# demo

![demo1](./doc/demo1.png)
![demo2](./doc/demo2.png)
