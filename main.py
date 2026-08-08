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
BASE_PRICE = 9.90
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


def sealed_hexagram_markup(completed):
    """Render a six-line casting animation without exposing any yin/yang result."""
    lines = []
    # A hexagram is traditionally drawn from the bottom (初爻) upwards.
    for index in range(5, -1, -1):
        is_sealed = index < completed
        is_current = index == completed and completed < 6
        classes = "sealed-line"
        if is_sealed:
            classes += " sealed"
        elif is_current:
            classes += " waiting"
        lines.append(f'<div class="{classes}"></div>')

    if completed == 0:
        status = "凝神静气，开始起卦"
    elif completed < 6:
        status = f"第 {completed} 爻已封存"
    else:
        status = "六爻已成，静待揭晓"

    return f"""
    <style>
      .casting-card {{
        max-width: 330px; margin: 8px auto 20px; padding: 26px 34px 22px;
        border: 1px solid #ead9b7; border-radius: 16px;
        background: linear-gradient(145deg, #fffdf7, #f7efe0); text-align: center;
      }}
      .casting-title {{ color: #7a5a2d; font-size: 14px; letter-spacing: 0.22em; margin-bottom: 20px; }}
      .sealed-lines {{ display: flex; flex-direction: column; gap: 10px; align-items: center; }}
      .sealed-line {{ width: 142px; height: 7px; border-radius: 9px; background: #ddd4c5; opacity: .55; }}
      .sealed-line.sealed {{ background: linear-gradient(90deg, #b98a42, #e4c77e, #a97831); opacity: 1; box-shadow: 0 2px 8px #d8bd7a77; }}
      .sealed-line.waiting {{ animation: sealPulse .65s ease-in-out infinite alternate; }}
      .casting-status {{ margin-top: 20px; color: #8b6b3d; font-size: 14px; }}
      @keyframes sealPulse {{ from {{ opacity: .32; transform: scaleX(.9); }} to {{ opacity: .9; transform: scaleX(1); }} }}
    </style>
    <div class="casting-card">
      <div class="casting-title">六 爻 封 卦</div>
      <div class="sealed-lines">{''.join(lines)}</div>
      <div class="casting-status">{status}</div>
    </div>
    """


def play_casting_animation():
    with st.chat_message("assistant"):
        placeholder = st.empty()
        for completed in range(7):
            placeholder.markdown(sealed_hexagram_markup(completed), unsafe_allow_html=True)
            if completed < 6:
                time.sleep(0.65)
        time.sleep(0.45)
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
            temperature=0.7,
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
                "content": "请从上一句自然续写，不要重复前文。用一两段完成即可，并在完整句子处收尾。",
            },
        ]

    return "\n\n".join(all_parts)


def initial_interpretation(reading):
    gua_des = reading["gua_des"]
    return ask_qwen([
        {
            "role": "system",
            "content": (
                "你是一位温和、清醒的易经决策陪伴者。根据用户的问题和卦象，帮助用户整理思路，"
                "不预测未来，不把任何结果说成必然发生。请用三个短部分回答：看见什么、要留意什么、下一步能做什么。"
                "每部分不超过三句话，务必在完整句子处结束。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户的问题：{reading['question']}\n六爻结果：{reading['gua']}\n"
                f"卦名：{gua_des['name']}\n{gua_des['des']}\n卦辞：{gua_des['sentence']}\n"
                "请给出一段有层次、易懂的初始解读。"
            ),
        },
    ])


def follow_up_interpretation(reading, follow_up_question):
    gua_des = reading["gua_des"]
    history = "\n".join(reading.get("followups", [])) or "（暂无）"
    return ask_qwen([
        {
            "role": "system",
            "content": (
                "你是一位温和、清醒的易经决策陪伴者。只围绕同一卦象回答追问，帮助用户梳理思路，不预测未来。"
                "回答要直接、完整，最多给三个要点；宁可简短，也不要在一句话或一个要点中间停止。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"原问题：{reading['question']}\n卦象：{reading['gua']}，{gua_des['name']}\n"
                f"卦辞：{gua_des['sentence']}\n此前追问：{history}\n\n本次追问：{follow_up_question}"
            ),
        },
    ], max_tokens=800)


def generate_reading(question):
    first_lines = []
    line_records = []
    for index in range(3):
        coins = get_3_coin()
        first_lines.append(yin_yang(coins))
        line_records.append(format_coin_result(coins, index))

    first_gua = gua_dict["".join(first_lines)]

    second_lines = []
    for index in range(3, 6):
        coins = get_3_coin()
        second_lines.append(yin_yang(coins))
        line_records.append(format_coin_result(coins, index))

    second_gua = gua_dict["".join(second_lines)]
    gua = second_gua + first_gua
    gua_des = des_dict[gua]
    play_casting_animation()
    add_message("assistant", "六爻已成。本次卦象已为你封存，等待揭晓。")
    return {
        "question": question,
        "gua": gua,
        "gua_des": gua_des,
        "line_records": line_records,
        "followups": [],
    }


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
    st.session_state.remaining_followups = 0
    st.rerun()


def render_payment_page():
    st.divider()
    st.subheader("揭晓本次卦象与完整解读")
    st.caption("本次卦象已经生成。付款后揭晓卦名、卦辞、AI 初始解读，以及围绕本卦的 5 次追问。")
    payment_method = st.radio("支付方式", ["微信支付", "支付宝支付"], horizontal=True)
    coupon_code = st.text_input("优惠码（可选）", placeholder="例如：TEST100")
    discount, coupon_text = coupon_discount(coupon_code)
    final_price = BASE_PRICE - discount

    if coupon_code and coupon_text:
        st.success(coupon_text)
    elif coupon_code:
        st.warning("优惠码无效")

    st.markdown(f"**本次专属问卦：¥{BASE_PRICE:.2f}**")
    if discount:
        st.markdown(f"优惠：-¥{discount:.2f}  ")
    st.markdown(f"### 应付：¥{final_price:.2f}")
    st.info("这是付款流程测试版：点击下方按钮不会真实扣款。")
    if st.button(f"模拟{payment_method}支付并揭晓", type="primary", use_container_width=True):
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
        st.session_state.reading = generate_reading(question)
        st.session_state.stage = "payment"
        st.rerun()
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
