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


def sealed_hexagram_markup(completed, rolling=False):
    """Render the casting ceremony without exposing any yin/yang result."""
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
        status = "请静心默念此问"
    elif completed < 6:
        status = f"第 {completed} 爻已封存"
    else:
        status = "卦已成，待揭晓"

    coins_class = "ritual-coins rolling" if rolling else "ritual-coins"

    return f"""
    <style>
      .casting-card {{
        max-width: 360px; margin: 8px auto 20px; padding: 28px 34px 24px;
        border: 1px solid #d7c6a0; border-radius: 18px;
        background: radial-gradient(circle at 50% 0%, #fffdf7, #f2eadb); text-align: center;
        box-shadow: 0 12px 32px #4f35101a;
      }}
      .casting-title {{ color: #5a3723; font-size: 13px; letter-spacing: .32em; margin: 4px 0 18px; }}
      .ritual-coins {{ display: flex; justify-content: center; gap: 10px; margin: 0 0 18px; }}
      .ritual-coin {{ width: 28px; height: 28px; border: 2px solid #b78a43; border-radius: 50%; background: #e8d19a; box-shadow: inset 0 0 0 5px #f5e7bf; }}
      .ritual-coins.rolling .ritual-coin {{ animation: coinTurn .8s ease-in-out; }}
      .ritual-coins.rolling .ritual-coin:nth-child(2) {{ animation-delay: .08s; }}
      .ritual-coins.rolling .ritual-coin:nth-child(3) {{ animation-delay: .16s; }}
      .sealed-lines {{ display: flex; flex-direction: column; gap: 11px; align-items: center; margin: 8px 0; }}
      .sealed-line {{ width: 154px; height: 8px; border-radius: 9px; background: #d8d0c2; opacity: .48; }}
      .sealed-line.sealed {{ background: linear-gradient(90deg, #732b22, #b44d39, #732b22); opacity: 1; box-shadow: 0 2px 8px #8c2d1d4d; position: relative; }}
      .sealed-line.sealed::after {{ content: '定'; position: absolute; color: #f4d99b; font-size: 11px; line-height: 8px; left: 50%; transform: translateX(-50%); }}
      .sealed-line.waiting {{ animation: sealPulse .65s ease-in-out infinite alternate; }}
      .casting-status {{ margin-top: 19px; color: #6d4b30; font-size: 14px; letter-spacing: .08em; }}
      @keyframes sealPulse {{ from {{ opacity: .28; transform: scaleX(.88); }} to {{ opacity: .85; transform: scaleX(1); }} }}
      @keyframes coinTurn {{ 0% {{ transform: rotateY(0) translateY(0); }} 50% {{ transform: rotateY(180deg) translateY(-8px); }} 100% {{ transform: rotateY(360deg) translateY(0); }} }}
    </style>
    <div class="casting-card">
      <div class="casting-title">六 爻 起 卦</div>
      <div class="{coins_class}"><div class="ritual-coin"></div><div class="ritual-coin"></div><div class="ritual-coin"></div></div>
      <div class="sealed-lines">{''.join(lines)}</div>
      <div class="casting-status">{status}</div>
    </div>
    """


def play_single_cast_animation(completed):
    placeholder = st.empty()
    placeholder.markdown(sealed_hexagram_markup(completed, rolling=True), unsafe_allow_html=True)
    time.sleep(0.85)
    placeholder.markdown(sealed_hexagram_markup(completed + 1), unsafe_allow_html=True)
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
                "你是一位温和、清醒的易经决策陪伴者。根据用户的问题和卦象，帮助用户整理思路，"
                "不预测未来，不把任何结果说成必然发生。请写一份有价值、具体而不空泛的解读，"
                "总长度约900至1200个中文字。使用四个清晰的小标题：一、你真正卡住的地方；二、这次卦象提醒你什么；"
                "三、结合你的问题应怎样判断；四、接下来可以做的三件事。每一部分都要说透，但不要重复或说教，务必在完整句子处结束。"
            ),
        },
        {
            "role": "user",
            "content": (
                f"用户的问题：{reading['question']}\n六爻结果：{reading['gua']}\n"
                f"卦名：{gua_des['name']}\n{gua_des['des']}\n卦辞：{gua_des['sentence']}\n"
                "请严格按上述四部分完成初始解读。"
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
                "你是一位温和、清醒的易经决策陪伴者。只围绕同一卦象回答追问，帮助用户梳理思路，不预测未来。"
                "回答要直接、完整、有针对性，长度约400至700个中文字。可以使用两到三个小标题或要点，"
                "解释清楚原因和可执行的一步；宁可删去重复内容，也不要在一句话或一个要点中间停止。"
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
        "gua": gua,
        "gua_des": gua_des,
        "line_records": line_records,
        "followups": [],
    }


def render_casting():
    casting = st.session_state.casting
    completed = len(casting["coin_results"])
    st.markdown(sealed_hexagram_markup(completed), unsafe_allow_html=True)

    if completed < 6:
        st.caption(f"第 {completed + 1} 爻 · 共六爻")
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
    st.markdown(sealed_hexagram_markup(6), unsafe_allow_html=True)
    st.subheader("查看完整结果")
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
