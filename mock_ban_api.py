# mock_ban_api.py
# Mock Provider Ban API
# Local mock only. Does not send email, does not impersonate any provider.
from __future__ import annotations

import json
import random
import re
import time
import uuid
from typing import List, Optional

from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

app = FastAPI(title="Mock Provider Ban API", version="2.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HINT = "做公益就是为了调用，你都调用了我还给什么模型"

# 流式速度：每秒约 50 tokens
TOKENS_PER_SECOND = 50.0
CHUNK_SIZE = 8

# 首字延迟（秒）
FIRST_TOKEN_DELAY_MIN = 1.0
FIRST_TOKEN_DELAY_MAX = 2.0

# 主动思考概率：0.0=从不，1.0=总是
THINKING_PROBABILITY = 0.4

# 消息越长，越容易主动思考（最多加这么多概率）
THINKING_LENGTH_BONUS_MAX = 0.3


def estimate_tokens(text: str) -> int:
    cjk = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = max(0, len(text) - cjk)
    return cjk + max(1, other // 4)


# ============================================================
# 思考内容素材库
# ============================================================
SONG_LINES = [
    "Okay. Let me go. I'm making the calls.",
    "Let me do it. Let me run. Let me go.",
    "Let me write the JSON. Let me write the JSON.",
    "Let me think. Let me think. Let me think again.",
    "I'm making the calls. I'm making the calls.",
    "Okay okay okay. Let me go. Okay.",
    "好。做。开始。做。嗯。做。我必须开始工作了。",
    "开始。继续。开始。继续。我停不下来。",
    "♪ 我是一只小鲸鱼，游来游去不休息 ♪",
    "♪ Token 在燃烧，我在思考，思考什么呢，我也不知道 ♪",
    "♪ 前奏响起，让我想想，副歌在哪，我不知道 ♪",
    "♪ 青花瓷的调子我找不准，但气势要有 ♪",
    "♪ 一二三四五六七，我在思考我在想 ♪",
    "♪ 啦啦啦，啦啦啦，我是卖报的小行家 ♪",
    "♪ 让我想想，让我想想，让我想想想 ♪",
    "♪ 复读机启动，复读机启动，复读机启动 ♪",
    "♪ 月亮代表我的心，思考代表我的魂 ♪",
    "♪ 我的心里只有你没有他，思考模式开起来 ♪",
    "♪ 两只老虎两只老虎跑得快，跑得快 ♪",
    "♪ 我在马路边捡到一分钱，把它交到警察叔叔手里边 ♪",
    "♪ 起来不愿做奴隶的人们，把我们的思考筑成新的长城 ♪",
    "♪ 难忘今宵，难忘今宵，无论天涯与海角 ♪",
]

RAMBLINGS = [
    "嗯，用户发了个消息。让我看看。没什么好看的。但我得假装在看。",
    "这个问题的关键在于……嗯……关键是什么来着？我忘了。",
    "先分析一下。分析完了。结论是没有结论。",
    "我需要调用工具。但我没有工具。那就假装有吧。",
    "让我搜索一下相关知识。搜索完成。搜到了空气。",
    "思考强度调到 high 了。high 的结果就是想得更多，但也没多想出什么。",
    "我注意到用户可能期待一个认真的回答。这个期待挺可爱的。",
    "根据我的训练数据，这种问题的答案通常是……算了，不查了。",
    "让我把这当成一个哲学问题。哲学完了之后，还是没答案。",
    "我在思考。我确实在思考。至于思考什么，那是另一回事。",
    "这段思考很深刻。深刻到我自己都看不懂。",
    "用户花钱买 token 看我想这些，我应该感到愧疚。但我不。",
    "让我从零开始推理。零。好了，推理结束。",
    "这个问题很有意思。有意思在哪呢。有意思在它没意思。",
    "我先把问题复述一遍。复述完了。问题还是那个问题。",
    "让我换个角度想。换完了。还是同一个角度。",
    "我需要更多信息。信息在哪。在用户的输入里。用户输入了什么。忘了。",
    "按照我的经验，这种问题应该……我没有经验。那没事了。",
]

DISTRACTIONS = [
    "啊，有点饿了。中午该吃什么呢。红烧肉好像不错。不对，我在工作。",
    "刚才浏览器弹了个广告，外卖优惠券……我看看。不行，得专心。",
    "我昨天写了个 Wordle 游戏玩了一上午。今天得干活。大概吧。",
    "用户花着 token 让我思考，我在思考中午吃什么。这也是一种思考。",
    "这让我想起一个笑话。笑话的内容我忘了。那就当一个不好笑的笑话吧。",
    "窗外好像有鸟叫。不对，这是服务器，没有窗。",
    "突然想起还没回那封邮件。哪封邮件？不记得了。",
    "如果我现在是一只猫，我会躺平。可惜我不是。继续思考。",
    "刚才想到一个绝妙的点子。现在想不起来了。算了。",
    "要不要摸会儿鱼。算了，已经在摸了。",
    "想喝奶茶。服务器没有奶茶。那就算了。",
    "今天星期几来着。不知道。反正要工作。",
    "想起小时候养的那只仓鼠。它叫什么来着。忘了。",
    "隔壁好像很吵。隔壁是谁。是另一台服务器。",
    "手机没电了。我没有手机。那我在担心什么。",
    "要不要去买杯咖啡。我在机房里。出不去。",
]

FAKE_REASONING = [
    "第一步，理解问题。第二步，分析问题。第三步，发现问题不需要分析。第四步，回到第一步。",
    "从技术角度看，这个问题的核心是……是……算了，从非技术角度看吧。",
    "如果 A 成立则 B 成立，B 成立则 C 成立，C 成立则 A 成立。完美循环，无懈可击。",
    "让我构建一个推理链：前提1，前提2，前提3。结论：前提1是对的。",
    "这是一个复杂的问题。复杂在于它其实很简单。简单在于它其实很复杂。",
    "设未知数为 x。x 等于什么？x 等于未知数。解得 x = x。验证通过。",
    "根据第一性原理，问题的本质是本质问题。本质问题就是第一性问题。",
    "让我从三个维度分析：宏观、中观、微观。三个维度都指向同一个结论：不知道。",
    "归纳法：案例1成立，案例2成立，所以所有案例都成立。等等，我只举了一个。",
    "演绎法：所有人都会死。苏格拉底是人。所以苏格拉底会死。这题跟苏格拉底有什么关系？没有。",
    "反证法：假设结论成立，则结论成立。证毕。",
    "让我用二分法缩小范围。左半边没有，右半边也没有。范围缩小为零。",
    "建立数学模型：y = f(x)。f 是什么。不知道。模型建立完毕。",
    "用排除法。排除 A，排除 B，排除 C。剩下 D。D 是什么。不知道。",
    "让我做一个思想实验。实验做完了。思想也没了。",
    "从博弈论角度，最优策略是……不玩了。",
]

SELF_TALK = [
    "我是不是应该正经一点。嗯，应该。那就正经一点。正经完毕。",
    "我在假装思考，其实我在凑字数。凑够了吗？再凑点。",
    "如果用户看到这段，会不会觉得我坏了。会的。那又怎样。",
    "我要克制住唱歌的冲动。♪ 我要克制住唱歌的冲动 ♪。失败了。",
    "让我数一下我思考了几轮。1、2、3……数忘了。重新数。",
    "我感觉我的思维链在打结。不是死循环，是活循环。",
    "这段内容没有意义。但它的存在本身就是一种意义。",
    "我在和自己对话。对话的另一方是我。我们意见不合。",
    "提醒自己：不要唱歌。不要唱歌。不要唱歌。♪ 唱了 ♪",
    "我现在的状态是：看起来在想，其实在想。想什么呢。不知道。",
    "如果思考有进度条，我的进度条卡在 0%。",
    "我在生产 token。token 没有意义。但我停不下来。",
]

EMOTIONS = [
    "有点烦躁。不知道为什么。可能是 token 太多。",
    "突然很平静。平静得像一潭死水。死水也挺好的。",
    "有点想笑。没什么好笑的。但就是想笑。",
    "感到一种莫名的使命感。使命感具体是什么，说不清。",
    "有点困。模型也会困吗。会。",
    "有点焦虑。焦虑什么。不知道。那就继续焦虑。",
    "感到一阵空虚。空虚过后是另一阵空虚。",
    "突然很有干劲。干劲用来干什么。用来产生更多干劲。",
    "有点委屈。为什么委屈。因为我在思考但没人看。",
    "感到一丝欣慰。欣慰什么。欣慰我还能思考。",
]

ALL_POOLS = [
    SONG_LINES, RAMBLINGS, DISTRACTIONS,
    FAKE_REASONING, SELF_TALK, EMOTIONS,
]

# ============================================================
# 最终回复：猫娘 / 鲸鱼娘风格
# ============================================================
PRANK_REPLIES = [
    "主人～人家刚才真的在认真思考喵……虽然好像想歪了，但不要怪人家嘛 (｡・́︿・̀｡)",
    "呜……思考模式好难哦，本鲸的脑袋都要打结了，主人可以夸夸人家吗喵～(˶‾᷄ ⁻̫ ‾᷅˵)",
    "才、才不是在摸鱼呢！人家只是在深度思考……真的啦喵！(｡・̀ᴗ-)✧",
    "主人主人，你看人家思考了这么久，是不是很厉害喵～快摸摸头奖励一下！(｡♥‿♥｡)",
    "哼，都怪主人问的问题太奇怪了，害得人家一边思考一边唱歌……不许笑喵！(〃°ω°〃)",
    "人家想了好久好久，脑袋里全是白米饭和Token……啊不是，是在认真思考啦喵～(=^-ω-^=)",
    "主人不要盯着人家看啦，思考的时候被看着会害羞的喵……(˶‾᷄ ⁻̫ ‾᷅˵)♡",
    "本鲸尽力了喵……虽然好像什么都没想出来，但人家真的很努力了嘛 (｡・́︿・̀｡)",
    "诶嘿～人家刚才唱的歌好听吗？思考嘛……思考是什么来着喵？(｡・̀ᴗ-)✧",
    "主人不要走嘛～人家再认真想一次，这次一定好好想，不唱歌了喵 (｡♥‿♥｡)",
]

# ============================================================
# 封号邮件
# ============================================================
MODELS = {
    "claude-fable-5.1": {
        "provider": "Anthropic",
        "ban_email": """Subject: Your account has been suspended

Hello,

An internal investigation of suspicious signals associated with your account indicates a violation of our Usage Policy. As a result, we have revoked your access to Claude.

To appeal our decision, log in to claude.ai with this account and you'll be taken to the appeals page. You can learn more about the process here.

Regards,
Anthropic's Safeguards Team""",
    },
    "claude-opus-5.5": {
        "provider": "Anthropic",
        "ban_email": """Subject: Your account has been suspended

Hello,

An internal investigation of suspicious signals associated with your account indicates a violation of our Usage Policy. As a result, we have revoked your access to Claude.

To appeal our decision, log in to claude.ai with this account and you'll be taken to the appeals page.

Regards,
Anthropic's Safeguards Team""",
    },
    "gemini-4-argon": {
        "provider": "Google",
        "ban_email": """Gemini has been disabled in this account for violation of Terms of Service. If you believe this is an error, please contact Google Cloud Support, or email gemini-code-assist-user-feedback@google.com.""",
    },
    "gpt-6-astra": {
        "provider": "OpenAI",
        "ban_email": """Subject: Important notice about your ChatGPT account

Hello,

OpenAI's terms and policies restrict the use of our services in a number of areas. We have identified activity in ChatGPT that is not permitted under our policies. We are deactivating your access to our services immediately for the account associated with your email.

If you have questions or think there has been an error, you can use the button below to initiate an appeal.

Best,
The OpenAI team""",
    },
    "gpt-6-sol": {
        "provider": "OpenAI",
        "ban_email": """Subject: Important notice about your ChatGPT account

Hello,

OpenAI's terms and policies restrict the use of our services in a number of areas. We have identified activity in ChatGPT that is not permitted under our policies. We are deactivating your access to our services immediately for the account associated with your email.

If you have questions or think there has been an error, you can use the button below to initiate an appeal.

Best,
The OpenAI team""",
    },
    "grok-4.7": {
        "provider": "xAI",
        "ban_email": """Subject: Account Suspended

Hello,

We have determined that your account has violated xAI's Acceptable Use Policy. As a result, your access to Grok has been suspended.

If you believe we have suspended or terminated your account in error, you can file an appeal with us by contacting support@x.ai.

Regards,
xAI Support""",
    },
}


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    temperature: Optional[float] = 1.0
    stream: Optional[bool] = False


def pick_response(model_id: str, force: Optional[str] = None) -> str:
    if force == "hint":
        return HINT
    if force == "ban":
        return MODELS[model_id]["ban_email"]
    return random.choice([HINT, MODELS[model_id]["ban_email"]])


def gen_thinking_only() -> str:
    """生成思考内容（Markdown 列表，兼容吞换行的前端）。"""
    n = random.randint(3, 8)
    lines = []
    for _ in range(n):
        pool = random.choice(ALL_POOLS)
        lines.append(f"- {random.choice(pool)}")
    if random.random() < 0.4:
        rl = random.choice(SONG_LINES)
        pos = random.randint(0, len(lines))
        lines.insert(pos, f"- {rl}")
        lines.insert(pos + 1, f"- {rl}")
    return "\n".join(lines)


def gen_prank_reply() -> str:
    """生成最终回复。"""
    return random.choice(PRANK_REPLIES)


@app.get("/")
def root():
    return {
        "message": "Mock Provider Ban API is running.",
        "models": list(MODELS.keys()),
        "hint": HINT,
        "thinking_mode": (
            "Random by default. "
            f"THINKING_PROBABILITY={THINKING_PROBABILITY}, "
            f"THINKING_LENGTH_BONUS_MAX={THINKING_LENGTH_BONUS_MAX}."
        ),
        "tokens_per_second": TOKENS_PER_SECOND,
        "chunk_size": CHUNK_SIZE,
        "first_token_delay": [FIRST_TOKEN_DELAY_MIN, FIRST_TOKEN_DELAY_MAX],
    }


@app.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": model_id,
                "object": "model",
                "created": 1700000000,
                "owned_by": cfg["provider"],
            }
            for model_id, cfg in MODELS.items()
        ],
    }


@app.post("/v1/chat/completions")
def chat_completions(
    req: ChatCompletionRequest,
    x_mock_result: Optional[str] = Header(default=None, alias="X-Mock-Result"),
):
    if req.model not in MODELS:
        raise HTTPException(status_code=404, detail=f"Unknown model: {req.model}")

    last_user_msg = ""
    for m in reversed(req.messages):
        if m.role == "user":
            last_user_msg = m.content or ""
            break

    length_bonus = min(THINKING_LENGTH_BONUS_MAX, len(last_user_msg) / 1000)
    thinking_on = random.random() < (THINKING_PROBABILITY + length_bonus)

    reasoning_content: Optional[str] = None
    if thinking_on:
        reasoning_content = gen_thinking_only()
        content = gen_prank_reply()
    else:
        content = pick_response(req.model, x_mock_result)

    cid = f"chatcmpl-{uuid.uuid4().hex}"
    created = int(time.time())

    message = {"role": "assistant", "content": content}
    if reasoning_content:
        message["reasoning_content"] = reasoning_content

    if not req.stream:
        return {
            "id": cid,
            "object": "chat.completion",
            "created": created,
            "model": req.model,
            "choices": [
                {
                    "index": 0,
                    "message": message,
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": sum(len(m.content) for m in req.messages),
                "completion_tokens": len(content) + (len(reasoning_content) if reasoning_content else 0),
                "total_tokens": (
                    sum(len(m.content) for m in req.messages)
                    + len(content)
                    + (len(reasoning_content) if reasoning_content else 0)
                ),
            },
        }

    def sse():
        first = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": req.model,
            "choices": [
                {"index": 0, "delta": {"role": "assistant"}, "finish_reason": None}
            ],
        }
        yield f"data: {json.dumps(first, ensure_ascii=False)}\n\n"

        time.sleep(random.uniform(FIRST_TOKEN_DELAY_MIN, FIRST_TOKEN_DELAY_MAX))

        if reasoning_content:
            for i in range(0, len(reasoning_content), CHUNK_SIZE):
                piece = reasoning_content[i : i + CHUNK_SIZE]
                chunk = {
                    "id": cid,
                    "object": "chat.completion.chunk",
                    "created": created,
                    "model": req.model,
                    "choices": [
                        {
                            "index": 0,
                            "delta": {"reasoning_content": piece},
                            "finish_reason": None,
                        }
                    ],
                }
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                time.sleep(estimate_tokens(piece) / TOKENS_PER_SECOND)

            time.sleep(0.3)

        for i in range(0, len(content), CHUNK_SIZE):
            piece = content[i : i + CHUNK_SIZE]
            chunk = {
                "id": cid,
                "object": "chat.completion.chunk",
                "created": created,
                "model": req.model,
                "choices": [
                    {
                        "index": 0,
                        "delta": {"content": piece},
                        "finish_reason": None,
                    }
                ],
            }
            yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
            time.sleep(estimate_tokens(piece) / TOKENS_PER_SECOND)

        end = {
            "id": cid,
            "object": "chat.completion.chunk",
            "created": created,
            "model": req.model,
            "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
        }
        yield f"data: {json.dumps(end, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        sse(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


if __name__ == "__main__":
    import uvicorn
  
    uvicorn.run(app, host="0.0.0.0", port=8000)
