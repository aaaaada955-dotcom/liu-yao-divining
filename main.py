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


def ask_qwen(messages, max_tokens=500):
    response = make_client().chat.completions.create(
        model="qwen-plus", messages=messages, temperature=0.7, max_tokens=max_tokens
    )
    answer = response.choices[0].message.content.strip()
    if not answer:
        raise RuntimeError("empty_response")
    return answer


def initial_interpretation(reading):
    gua_des = reading["gua_des"]
    return ask_qwen([
        {
            "role": "system",
            "content": (
                "你是一位温和、清醒的易经决策陪伴者。根据用户的问题和卦象，帮助用户整理思路，"
                "不预测未来，不把任何结果说成必然发生。给出具体、不过度承诺的建议。"
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
            "content": "你是一位温和、清醒的易经决策陪伴者。只围绕同一卦象回答追问，帮助用户梳理思路，不预测未来。",
        },
        {
            "role": "user",
            "content": (
                f"原问题：{reading['question']}\n卦象：{reading['gua']}，{gua_des['name']}\n"
                f"卦辞：{gua_des['sentence']}\n此前追问：{history}\n\n本次追问：{follow_up_question}"
            ),
        },
    ], max_tokens=400)


def generate_reading(question):
    first_lines = []
    for index in range(3):
        coins = get_3_coin()
        first_lines.append(yin_yang(coins))
        add_message("assistant", format_coin_result(coins, index))

    first_gua = gua_dict["".join(first_lines)]
    add_message("assistant", f"您的首卦为：**{first_gua}**")

    second_lines = []
    for index in range(3, 6):
        coins = get_3_coin()
        second_lines.append(yin_yang(coins))
        add_message("assistant", format_coin_result(coins, index))

    second_gua = gua_dict["".join(second_lines)]
    gua = second_gua + first_gua
    gua_des = des_dict[gua]
    add_message("assistant", f"您的次卦为：**{second_gua}**")
    add_message(
        "assistant",
        f"### 本次卦象：{gua_des['name']}\n{gua_des['des']}  \n\n> {gua_des['sentence']}",
        delay=0,
    )
    return {"question": question, "gua": gua, "gua_des": gua_des, "followups": []}


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
    st.subheader("解锁本次完整解读")
    st.caption("包含 AI 初始解读，以及围绕本卦的 5 次追问。新的问题需要重新起一卦。")
    payment_method = st.radio("支付方式", ["微信支付", "支付宝支付"], horizontal=True)
    coupon_code = st.text_input("优惠码（可选）", placeholder="例如：TEST100")
    discount, coupon_text = coupon_discount(coupon_code)
    final_price = BASE_PRICE - discount

    if coupon_code and coupon_text:
        st.success(coupon_text)
    elif coupon_code:
        st.warning("优惠码无效")

    st.markdown(f"**本次完整解读：¥{BASE_PRICE:.2f}**")
    if discount:
        st.markdown(f"优惠：-¥{discount:.2f}  ")
    st.markdown(f"### 应付：¥{final_price:.2f}")
    st.info("这是付款流程测试版：点击下方按钮不会真实扣款。")
    if st.button(f"模拟完成{payment_method}支付", type="primary", use_container_width=True):
        st.session_state.stage = "interpreting"
        st.session_state.reading["payment_method"] = payment_method
        st.session_state.reading["paid_price"] = final_price
        st.rerun()


def finish_test_payment():
    reading = st.session_state.reading
    add_message("assistant", f"✅ 已完成{reading['payment_method']}测试支付，本次解读已解锁。")
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
