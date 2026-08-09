import json
import os
import random
import time

import streamlit as st
from dotenv import load_dotenv
from openai import (
    APIConnectionError,
    APIStatusError,
    AuthenticationError,
    OpenAI,
    OpenAIError,
    RateLimitError,
)

load_dotenv()

# 测试阶段的展示价格。正式上线前改这里即可。
BASE_PRICE = 20.00
TEST_COUPONS = {
    "TEST100": {"type": "percent", "value": 100, "label": "测试体验券：立减全部金额"},
    "WELCOME2": {"type": "amount", "value": 2, "label": "新人体验券：立减 ¥2"},
}

gua_dict = {
    "阳阳阳": "乾", "阴阴阴": "坤", "阴阳阳": "兑", "阳阴阳": "震",
    "阳阳阴": "巽", "阴阳阴": "坎", "阳阴阴": "艮", "阴阴阳": "离",
}
number_dict = {0: "初爻", 1: "二爻", 2: "三爻", 3: "四爻", 4: "五爻", 5: "六爻"}

with open("gua.json", encoding="utf-8") as gua_file:
    des_dict = json.load(gua_file)

st.set_page_config(page_title="AI 易经决策助手", page_icon="☯", layout="centered")


def init_state():
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": "静一静，告诉我此刻最想理清的一件事。"}
        ]
    if "stage" not in st.session_state:
        st.session_state.stage = "ask"
    if "reading" not in st.session_state:
        st.session_state.reading = None
    if "remaining_followups" not in st.session_state:
        st.session_state.remaining_followups = 0
    if "casting" not in st.session_state:
        st.session_state.casting = None


def render_history():
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def add_message(role, content, delay=0.01):
    st.session_state.messages.append({"role": role, "content": content})
    with st.chat_message(role):
        placeholder = st.empty()
        if role == "assistant" and delay:
            shown = ""
            for character in content:
                shown += character
                placeholder.markdown(shown + "▌")
                time.sleep(delay)
            placeholder.markdown(shown)
        else:
            placeholder.markdown(content)


def get_3_coin():
    return [random.randint(0, 1) for _ in range(3)]


def yin_yang(coin_result):
    return "阳" if sum(coin_result) > 1.5 else "阴"


def format_coin_result(coin_result, index):
    sides = "".join("背" if item > 0.5 else "字" for item in coin_result)
    return f"{number_dict[index]}：{sides}，为 {yin_yang(coin_result)}"


def coin_markup(value, rolling=False):
    side = "正" if value else "反"
    rolling_class = " coin-rolling" if rolling else ""
    return f'<div class="ancient-coin{rolling_class}"><span class="coin-word">{side}</span><i></i></div>'


def casting_markup(coin_results, rolling=False):
    """Show each cast openly, but keep the final hexagram sealed until payment."""
    completed = len(coin_results)
    groups = []
    for index, result in enumerate(coin_results):
        coins = "".join(coin_markup(value) for value in result)
        groups.append(f'<div class="cast-record"><b>{number_dict[index]}</b><div class="coin-row small">{coins}</div><span>落定：{yin_yang(result)}爻</span></div>')
    if rolling:
        groups.append(f'<div class="casting-now"><div>第 {completed + 1} 爻 · 六爻之一</div><div class="coin-row">{coin_markup(0, True)}{coin_markup(1, True)}{coin_markup(0, True)}</div><em>三枚古钱正在翻转…</em></div>')
    elif completed < 6:
        groups.append(f'<div class="casting-now quiet"><div>第 {completed + 1} 爻 · 六爻之一</div><p>请静心默念此问</p></div>')
    else:
        groups.append('<div class="sealed-chart"><div class="ink-lines">☷<br>☳</div><div class="vermilion-seal">卦<br>已<br>封</div></div><div class="sealed-status">卦已成，待解读</div>')
    return f"""
    <style>
      .casting-card {{
        max-width: 460px; margin: 8px auto 20px; padding: 28px 28px 24px;
        border: 1px solid #d7c6a0; border-radius: 18px;
        background: radial-gradient(circle at 50% 0%, #fffdf7, #f2eadb); text-align: center;
        box-shadow: 0 12px 32px #4f35101a;
      }}
      .casting-title {{ color: #5a3723; font-size: 13px; letter-spacing: .32em; margin: 4px 0 18px; }}
      .cast-record {{ border-top: 1px solid #ddcfb6; padding: 10px 0; display:grid; grid-template-columns:62px 1fr 82px; align-items:center; color:#684b31; font-size:13px; }}
      .coin-row {{ display:flex; justify-content:center; gap:16px; margin:16px 0; perspective:500px; }} .coin-row.small {{ justify-content:flex-start; gap:5px; margin:0; }}
      .ancient-coin {{ width:58px; height:58px; border-radius:50%; position:relative; display:grid; place-items:center; color:#5a3513; font-weight:700; font-family:serif; background:radial-gradient(circle at 33% 25%,#fff1bd 0 7%,#d8a94f 25%,#8b5720 57%,#e1ba63 65%,#6d3d13 75%,#e5c06c 79%,#9a6427 100%); box-shadow:inset 0 0 0 3px #f3d88c,inset 0 0 0 7px #8e571e,0 5px 8px #42240d42; }}
      .ancient-coin::before {{ content:''; width:17px; height:17px; background:#f4ead7; border:3px solid #87531e; box-shadow:inset 0 0 4px #5a3513; }} .ancient-coin::after {{ content:'乾 隆 通 宝'; position:absolute; font-size:6px; letter-spacing:1px; top:6px; }} .ancient-coin i {{ position:absolute; inset:10px; border:1px dashed #f3d88c; border-radius:50%; }} .coin-word {{ z-index:2; font-size:11px; background:#d8a94f; padding:1px; }}
      .coin-row.small .ancient-coin {{ width:29px;height:29px; }} .coin-row.small .ancient-coin::before {{ width:8px;height:8px;border-width:2px; }} .coin-row.small .ancient-coin::after,.coin-row.small .ancient-coin i {{ display:none; }} .coin-row.small .coin-word {{ font-size:8px; }}
      .coin-rolling {{ animation: coinTurn .8s ease-in-out; }} .coin-rolling:nth-child(2) {{ animation-delay:.06s; }} .coin-rolling:nth-child(3) {{ animation-delay:.12s; }}
      .casting-now {{ padding:14px 0 6px; color:#5b3b24; font-size:15px; }} .casting-now em {{ font-size:12px;color:#9b7656; }} .casting-now.quiet p {{ margin:12px 0;color:#815d3a; }}
      .sealed-chart {{ height:154px; margin:20px auto 8px; position:relative; display:grid;place-items:center; background:linear-gradient(135deg,#e9dfcd,#c6b79c); border:1px solid #a6906a; overflow:hidden; }} .ink-lines {{ font-size:56px; line-height:.68; color:#423324; opacity:.42; letter-spacing:18px; transform:rotate(-4deg); }} .vermilion-seal {{ position:absolute; width:82px;height:82px;border-radius:50%;display:grid;place-items:center;line-height:1.05; font-weight:700;color:#f3c99f;background:#9d2b20; border:4px double #e6ab80; box-shadow:0 3px 8px #4b1a1670; transform:rotate(-10deg); }} .sealed-status {{ color:#782b22;font-weight:700;letter-spacing:.16em;margin-top:14px; }}
      @keyframes coinTurn {{ 0% {{ transform:rotateY(0) translateY(0); }} 45% {{ transform:rotateY(180deg) translateY(-13px) scale(1.06); }} 100% {{ transform:rotateY(360deg) translateY(0); }} }}
    </style>
    <div class="casting-card">
      <div class="casting-title">六 爻 起 卦</div>{''.join(groups)}
    </div>
    """


def play_single_cast_animation(completed):
    placeholder = st.empty()
    placeholder.markdown(casting_markup(st.session_state.casting['coin_results'], rolling=True), unsafe_allow_html=True)
    time.sleep(0.85)
    placeholder.empty()
    time.sleep(0.25)
    placeholder.empty()


def get_secret(name):
    value = os.getenv(name)
    if value:
        return value
    try:
        return st.secrets.get(name)
    except Exception:
        return None


def make_client():
    api_key = get_secret("DASHSCOPE_API_KEY")
    base_url = get_secret("DASHSCOPE_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("missing_ai_configuration")
    return OpenAI(api_key=api_key, base_url=base_url, timeout=30.0, max_retries=1)


def ask_qwen(messages, max_tokens=800):
    """Ask Qwen, and automatically continue once if the provider cuts it off mid-answer."""
    all_parts = []
    current_messages = list(messages)

    for _ in range(2):
        response = make_client().chat.completions.create(
            model="qwen-plus",
            messages=current_messages,
            temperature=0.55,
            max_tokens=max_tokens,
        )
        choice = response.choices[0]
        answer = (choice.message.content or "").strip()
        if not answer:
            raise RuntimeError("empty_response")
        all_parts.append(answer)

        # "length" means the answer reached the output limit before it was finished.
        if choice.finish_reason != "length":
            break
        current_messages = current_messages + [
            {"role": "assistant", "content": answer},
            {
                "role": "user",
                "content": "请从上一句自然续写，不要重复前文。保持原有结构，在完整句子处收尾。",
            },
        ]

    return "\n\n".join(all_parts)


def initial_interpretation(reading):
    gua_des = reading["gua_des"]
    return ask_qwen([
        {
            "role": "system",
            "content": (
                "你是有洞察力、说人话的易经解读者。用户付费是为了得到对自己这一个问题真正有用的回答，"
                "不是为了看通用心理鸡汤或固定模板。先在开头直接回应用户问的事情本身；再自然地结合卦象说明判断，"
                "最后给出真正贴合此事的观察或建议。文章组织必须由问题决定：感情问题可谈关系的走向、双方互动和关键节点；"
                "事业问题可谈机会、阻力和取舍；不要强行使用固定标题、固定段落或固定“三件事”。"
                "只能依据用户明确写出的问题和提供的卦象推断。绝不猜测昵称、地名、职业或人物称呼的含义；绝不虚构双方已有互动、"
                "性格、动机、感情状态或用户的行为。事实不足时，明确说“从这次问卦本身无法确认”，再说明可观察什么。"
                "可以对趋势作有分寸的判断，例如“更像”“目前倾向于”“若持续出现某种情况”，但不许宣称命运注定。"
                "不要复述或生硬搬运卦辞，不要使用少女攀附、主从、名分锚点、能量等说教或冒犯性措辞。"
                "语言自然、具体、有温度，约800至1200字；可以按内容自拟一两个短标题，也可以不设标题。务必完整收尾。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户的问题：{reading['question']}\n六爻结果：{reading['gua']}\n"
                f"卦名：{gua_des['name']}\n{gua_des['des']}\n卦辞：{gua_des['sentence']}\n"
                "请围绕用户这一个具体问题，写一篇自然、贴题、可读的解读。"
            ),
        },
    ], max_tokens=1600)


def follow_up_interpretation(reading, follow_up_question):
    gua_des = reading["gua_des"]
    history = "\n".join(reading.get("followups", [])) or "（暂无）"
    return ask_qwen([
        {
            "role": "system",
            "content": (
                "你是有洞察力、说人话的易经解读者。只围绕同一卦象和用户本次追问回答。先直接回答追问，"
                "再说明卦象为何支持这个判断；不要套固定模板或重复上一轮。不能从昵称、称呼或地名臆测人物背景，"
                "也不能把未提供的互动、动机和事实当作已知。信息不足时坦诚说明，并给出用户真正能观察或判断的点。"
                "不要预测必然结果、不要鸡汤、不要生硬搬运卦辞。长度约450至750字，自然组织，完整收尾。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原问题：{reading['question']}\n卦象：{reading['gua']}，{gua_des['name']}\n"
                f"卦辞：{gua_des['sentence']}\n此前追问：{history}\n\n本次追问：{follow_up_question}"
            ),
        },
    ], max_tokens=1100)


def create_reading(question, coin_results):
    first_lines = []
    line_records = []
    for index in range(3):
        coins = coin_results[index]
        first_lines.append(yin_yang(coins))
        line_records.append(format_coin_result(coins, index))

    first_gua = gua_dict["".join(first_lines)]

    second_lines = []
    for index in range(3, 6):
        coins = coin_results[index]
        second_lines.append(yin_yang(coins))
        line_records.append(format_coin_result(coins, index))

    second_gua = gua_dict["".join(second_lines)]
    gua = second_gua + first_gua
    gua_des = des_dict[gua]
    return {
        "question": question,
        "coin_results": coin_results,
        "gua": gua,
        "gua_des": gua_des,
        "line_records": line_records,
        "followups": [],
    }


def render_casting():
    casting = st.session_state.casting
    completed = len(casting["coin_results"])
    st.markdown(casting_markup(casting["coin_results"]), unsafe_allow_html=True)

    if completed < 6:
        if st.button("落下一爻", type="primary", use_container_width=True):
            play_single_cast_animation(completed)
            casting["coin_results"].append(get_3_coin())
            if len(casting["coin_results"]) == 6:
                st.session_state.reading = create_reading(casting["question"], casting["coin_results"])
                st.session_state.casting = None
                st.session_state.stage = "payment"
            st.rerun()
    else:
        st.session_state.reading = create_reading(casting["question"], casting["coin_results"])
        st.session_state.casting = None
        st.session_state.stage = "payment"
        st.rerun()


def reveal_reading(reading):
    gua_des = reading["gua_des"]
    add_message("assistant", "### 本次卦象揭晓", delay=0)
    add_message("assistant", "  \n".join(reading["line_records"]), delay=0)
    add_message(
        "assistant",
        f"### {gua_des['name']}\n{gua_des['des']}  \n\n> {gua_des['sentence']}",
        delay=0,
    )


def coupon_discount(code):
    coupon = TEST_COUPONS.get(code.strip().upper())
    if not coupon:
        return 0.0, None
    if coupon["type"] == "percent":
        return round(BASE_PRICE * coupon["value"] / 100, 2), coupon["label"]
    return min(float(coupon["value"]), BASE_PRICE), coupon["label"]


def reset_for_new_reading():
    st.session_state.messages = [{"role": "assistant", "content": "静一静，告诉我此刻最想理清的一件事。"}]
    st.session_state.stage = "ask"
    st.session_state.reading = None
    st.session_state.casting = None
    st.session_state.remaining_followups = 0
    st.rerun()


def render_payment_page():
    st.divider()
    st.markdown(casting_markup(st.session_state.reading.get("coin_results", [])), unsafe_allow_html=True)
    st.subheader("卦已成，待解读")
    st.caption("本次卦象已经生成。付款后查看卦名、卦辞、AI 初始解读，以及围绕本卦的 5 次追问。")
    payment_method = st.radio("支付方式", ["微信支付", "支付宝支付"], horizontal=True)
    coupon_code = st.text_input("优惠码（可选）", placeholder="例如：TEST100")
    discount, coupon_text = coupon_discount(coupon_code)
    final_price = BASE_PRICE - discount

    if coupon_code and coupon_text:
        st.success(coupon_text)
    elif coupon_code:
        st.warning("优惠码无效")

    st.markdown(f"**本次专属问卦：¥{BASE_PRICE:.0f}**")
    if discount:
        st.markdown(f"优惠：-¥{discount:.2f}  ")
    st.markdown(f"### 应付：¥{final_price:.2f}")
    st.info("这是付款流程测试版：点击下方按钮不会真实扣款。")
    if st.button("查看完整结果 · ¥20", type="primary", use_container_width=True):
        st.session_state.stage = "interpreting"
        st.session_state.reading["payment_method"] = payment_method
        st.session_state.reading["paid_price"] = final_price
        st.rerun()


def finish_test_payment():
    reading = st.session_state.reading
    add_message("assistant", f"✅ 已完成{reading['payment_method']}测试支付，本次解读已解锁。")
    reveal_reading(reading)
    try:
        with st.spinner("正在整理这次卦象的解读……"):
            answer = initial_interpretation(reading)
        add_message("assistant", answer)
    except (RuntimeError, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError, OpenAIError):
        add_message("assistant", "这次暂时没有拿到 AI 解读。卦象已保留；请稍后重新进入本次问卦。")
    st.session_state.remaining_followups = 5
    st.session_state.stage = "followup"
    st.rerun()


def render_followup():
    remaining = st.session_state.remaining_followups
    st.info(f"本次卦象还可追问 **{remaining} 次**。请只围绕这一次问卦继续问。")
    question = st.chat_input(f"围绕本卦追问（还可问 {remaining} 次）")
    if question:
        add_message("user", question, delay=0)
        try:
            with st.spinner("正在回应你的追问……"):
                answer = follow_up_interpretation(st.session_state.reading, question)
            st.session_state.reading["followups"].append(question)
            add_message("assistant", answer)
        except (RuntimeError, AuthenticationError, RateLimitError, APIConnectionError, APIStatusError, OpenAIError):
            add_message("assistant", "这次追问暂时没有得到回应，请稍后再试；本次次数没有扣除。")
            return

        st.session_state.remaining_followups -= 1
        if st.session_state.remaining_followups == 0:
            st.session_state.stage = "finished"
            add_message("assistant", "本次问卦的 5 次追问已使用完。若有新的困扰，请重新起一卦。")
        st.rerun()


init_state()

st.title("AI 易经决策助手")
st.caption("用一次有仪式感的问卦，帮助你把心里的事理清一点。仅作思考陪伴，不替你预测未来或做决定。")
render_history()

if st.session_state.stage == "ask":
    question = st.chat_input("输入你此刻最想问的一件事")
    if question:
        add_message("user", question, delay=0)
        st.session_state.casting = {"question": question, "coin_results": []}
        st.session_state.stage = "casting"
        st.rerun()
elif st.session_state.stage == "casting":
    render_casting()
elif st.session_state.stage == "payment":
    render_payment_page()
elif st.session_state.stage == "interpreting":
    finish_test_payment()
elif st.session_state.stage == "followup":
    render_followup()
elif st.session_state.stage == "finished":
    st.success("本次问卦已完成。")
    if st.button("开始一次新的问卦", use_container_width=True):
        reset_for_new_reading()
