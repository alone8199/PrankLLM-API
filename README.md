# Mock Provider Ban API

一个本地模拟的 OpenAI 兼容接口。

它不连接任何真实厂商，不发送任何邮件，也不做任何网络请求。它只做一件事：**在你调用聊天接口时，返回一些你意想不到的东西。**

---

## 这是什么

这是一个整蛊型的 API 模拟器。它模仿了几家主流 AI 厂商的接口格式，但返回的内容并不是真正的回答，而是两类内容之一：

- **普通模式**：对应厂商的封号邮件，或一句固定的中文提示。
- **思考模式**：一段看起来像模像样的“思考过程”，最后接一句角色化的回复。

它兼容 OpenAI 的 Chat Completions 协议，因此可以被任何支持自定义 Base URL 的客户端直接调用。

## 它长什么样

一次调用，可能得到封号邮件：

```
Subject: Important notice about your ChatGPT account

Hello,

OpenAI's terms and policies restrict the use of our services in a number of areas.
We have identified activity in ChatGPT that is not permitted under our policies.
We are deactivating your access to our services immediately for the account
associated with your email.

If you have questions or think there has been an error, you can use the button
below to initiate an appeal.

Best,
The OpenAI team
```

也可能得到固定提示：

```
做公益就是为了调用，你都调用了我还给什么模型
```

还可能先“思考”一番，再回复：

```
[思考内容]
- 我在假装思考，其实我在凑字数。凑够了吗？再凑点。
- Let me think. Let me think. Let me think again.
- ♪ 月亮代表我的心，思考代表我的魂 ♪
- 演绎法：所有人都会死。苏格拉底是人。所以苏格拉底会死。这题跟苏格拉底有什么关系？没有。

[最终回复]
主人不要走嘛～人家再认真想一次，这次一定好好想，不唱歌了喵 (｡♥‿♥｡)
```

## 特性

- **OpenAI 兼容**：`/v1/chat/completions` 和 `/v1/models`，任何 OpenAI SDK 或客户端都能用。
- **多厂商模拟**：Anthropic、OpenAI、Google、xAI 四家的模型 ID 与封号文案。
- **主动思考**：思考模式不是靠开关，是服务端随机决定的。同一次对话，可能直接回复，也可能先思考再回复。
- **流式支持**：支持 `stream: true`，按约 50 tokens/秒的速度逐字输出，带首字延迟。
- **思考与回复分离**：思考内容放在 `reasoning_content` 字段，最终回复放在 `content` 字段，兼容 DeepSeek 系客户端的折叠显示。
- **CORS 全开**：浏览器直接调也不会有跨域问题。
- **零依赖外部资源**：所有内容内嵌在脚本里，不需要额外文件。

## 快速开始

安装依赖：

```bash
pip install fastapi uvicorn
```

启动：

```bash
python3 mock_ban_api.py
```

服务默认监听 `0.0.0.0:8000`。

调用：

```bash
curl -s -X POST http://127.0.0.1:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-6-astra",
    "messages": [{"role": "user", "content": "hi"}]
  }'
```

## 支持的模型

| 模型 ID | 厂商 |
|---------|------|
| `claude-fable-5.1` | Anthropic |
| `claude-opus-5.5` | Anthropic |
| `gemini-4-argon` | Google |
| `gpt-6-astra` | OpenAI |
| `gpt-6-sol` | OpenAI |
| `grok-4.7` | xAI |

## 接口

### `GET /`

返回服务信息与当前参数。

### `GET /v1/models`

返回模型列表。

### `POST /v1/chat/completions`

聊天补全接口。请求体兼容 OpenAI 格式：

```json
{
  "model": "gpt-6-astra",
  "messages": [{"role": "user", "content": "hi"}],
  "stream": false
}
```

不校验 API Key，客户端里随便填即可。

## 响应结构

### 普通模式

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": "Subject: Important notice about your ChatGPT account\n\n..."
    }
  }]
}
```

### 思考模式

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "reasoning_content": "- 我在假装思考...\n- Let me think...\n- ♪ 月亮代表我的心 ♪",
      "content": "主人不要走嘛～人家再认真想一次..."
    }
  }]
}
```

流式模式下，先推送 `delta.reasoning_content`，停顿后推送 `delta.content`。

## 触发逻辑

思考模式是**随机主动触发**的，客户端无需任何设置。

- 基础概率 40%
- 消息越长，触发概率越高，最多再增加 30%

短消息大约四成概率会思考，长消息大约七成。

## 可调参数

脚本顶部提供以下常量：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `TOKENS_PER_SECOND` | `50.0` | 流式输出速度 |
| `CHUNK_SIZE` | `8` | 每个流式分片的字符数 |
| `FIRST_TOKEN_DELAY_MIN` | `1.0` | 首字延迟下限（秒） |
| `FIRST_TOKEN_DELAY_MAX` | `2.0` | 首字延迟上限（秒） |
| `THINKING_PROBABILITY` | `0.4` | 主动思考基础概率 |
| `THINKING_LENGTH_BONUS_MAX` | `0.3` | 消息长度带来的额外概率 |

改完重启服务即可生效。

## 客户端兼容

任何兼容 OpenAI 协议的客户端都能使用，只需填写：

- Base URL：`http://<主机>:8000/v1`
- API Key：随意
- 模型：上表中的任意一个

支持 `reasoning_content` 的客户端（如 Cherry Studio、LobeChat、OpenWebUI）会把思考内容折叠显示，最终回复正常展示；不支持的客户端会忽略思考内容，只显示最终回复。

## 设计说明

- **普通模式**的文案取自公开网络信息或厂商典型通知格式。
- **思考模式**的素材来源包括模型思维链中“唱歌”的公开讨论、经典“走神”案例，以及一些自嘲式的内心独白。
- 思考内容以 Markdown 列表呈现，即使某些前端吞掉换行，也能通过列表符号看出条目结构。
- 最终回复采用角色化口吻，与思考内容形成反差。

## 免责声明

本项目仅用于本地测试与娱乐。

- 所有“封号邮件”内容均来自公开网络信息或典型通知格式，**不会真实发送**。
- 不代表任何厂商，也不与任何厂商官方有关。
- 请勿将其用于欺骗、冒充或其他不当用途。
