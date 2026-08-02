import time
import streamlit as st
import random
import json
import os
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

gua_dict = {
    '阳阳阳': '乾',
    '阴阴阴': '坤',
    '阴阳阳': '兑',
    '阳阴阳': '震',
    '阳阳阴': '巽',
    '阴阳阴': '坎',
    '阳阴阴': '艮',
    '阴阴阳': '离'
}

number_dict = {
    0: '初爻',
    1: '二爻',
    2: '三爻',
    3: '四爻',
    4: '五爻',
    5: '六爻',
}

with open('gua.json') as gua_file:
  file_contents = gua_file.read()
des_dict = json.loads(file_contents)


st.set_page_config(
    page_title="六爻游戏",
    page_icon="🔮",
    layout="centered",
)

st.markdown('## 六爻游戏')
st.markdown(""" 
> 本网站**仅供娱乐**，并非用来算命、迷信或卜卦的工具。所有的结果都是随机生成的，我们强烈建议用户不要受其内容的影响来做出任何决策。  
> 此外，其生成结果的过程仅供参考，只是游戏流程的一部分，不代表任何正统操作。  
> 本网站只是为了测试和娱乐，不允许用于商业用途，所有的内容都不能当作真实的，未成年人请勿使用。请各位用户理性对待，保持娱乐的心态，不要依赖或深信其结果。  
              
🥺   
试试作者的 [其他作品](https://kaiyi.cool)   
玩的开心记得点个 star 呀 [网站源代码](https://github.com/RealKai42/liu-yao-divining)     
""")
st.markdown("""
            六爻为丢 **六次** 三枚硬币，根据三枚硬币的正反（字背）对应本次阴阳，三次阴阳对应八卦中的一卦  
            六次阴阳对应六爻，六爻组合成两个八卦，对应八八六十四卦中的卦辞，根据卦辞进行 **随机** 解读  
              
            为保证可用性和成本限制，每次只能提问**一个问题**，请谨慎提问
            """)

if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": [{"type": "text", "content": "告诉我你心中的疑问吧 ❤️"}]
    }]
if "disable_input" not in st.session_state:
    st.session_state.disable_input = False

for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        for content in message["content"]:
            if content["type"] == "text":
                st.markdown(content["content"])
            elif content["type"] == "image":
                st.image(content["content"])
            elif content["type"] == "video":
                st.video(content["content"])


def add_message(role, content, delay=0.05):
     with st.chat_message(role):
        message_placeholder = st.empty()
        full_response = ""

        for chunk in list(content):
            full_response += chunk + ""
            time.sleep(delay)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)


def get_3_coin():
    return [random.randint(0, 1) for _ in range(3)]

def get_yin_yang_for_coin_res(coin_result):
    return "阳" if sum(coin_result) > 1.5 else "阴"

def get_number_for_coin_res(coin_result):
    return 1 if sum(coin_result) > 1.5 else 0

def format_coin_result(coin_result, i):
    return f"{number_dict[i]} 为 " + "".join([f"{'背' if i>0.5 else '字'}" for i in coin_result]) + " 为 " + get_yin_yang_for_coin_res(coin_result)

def disable():
    st.session_state["disable_input"] = True


def get_api_key():
    """Read the key locally from .env, or from Streamlit's private deployment settings."""
    api_key = os.getenv("OPENAI_API_KEY")
    if api_key:
        return api_key

    try:
        return st.secrets.get("OPENAI_API_KEY")
    except Exception:
        return None


def get_ai_interpretation(question, gua, gua_des):
    api_key = get_api_key()
    if not api_key:
        raise RuntimeError("missing_api_key")

    client = OpenAI(api_key=api_key, timeout=30.0, max_retries=1)
    response = client.responses.create(
        model="gpt-4o-mini",
        instructions=(
            "你是一位温和、清醒的易经决策陪伴者。根据用户的问题和卦象，"
            "帮助用户整理思路，不预测未来，也不把任何结果说成必然发生。"
            "给出积极、具体、不过度承诺的建议。"
        ),
        input=(
            f"问题是：{question}\n"
            f"六爻结果是：{gua}\n"
            f"卦名为：{gua_des['name']}\n"
            f"{gua_des['des']}\n"
            f"卦辞为：{gua_des['sentence']}"
        ),
        max_output_tokens=500,
    )

    interpretation = response.output_text.strip()
    if not interpretation:
        raise RuntimeError("empty_response")
    return interpretation

if question := st.chat_input(placeholder="输入你内心的疑问", key='input', disabled=st.session_state.disable_input, on_submit=disable):
    add_message("user", question)
    first_yin_yang = []
    for i in range(3):
        coin_res = get_3_coin()
        first_yin_yang.append(get_yin_yang_for_coin_res(coin_res))
        add_message("assistant", format_coin_result(coin_res, i))

    first_gua = gua_dict["".join(first_yin_yang)]
    add_message("assistant", f"您的首卦为：{first_gua}")

    second_yin_yang = []
    for i in range(3, 6):
        coin_res = get_3_coin()
        second_yin_yang.append(get_yin_yang_for_coin_res(coin_res))
        add_message("assistant", format_coin_result(coin_res, i))
    second_gua = gua_dict["".join(second_yin_yang)]
    add_message("assistant", f"您的次卦为：{second_gua}")

    gua = second_gua + first_gua
    gua_des = des_dict[gua]
    add_message("assistant", f"""
        六爻结果: {gua}  
        卦名为：{gua_des['name']}   
        {gua_des['des']}   
        卦辞为：{gua_des['sentence']}   
    """)

    try:
        with st.spinner('加载解读中，请稍等 ......'):
            interpretation = get_ai_interpretation(question, gua, gua_des)
        add_message("assistant", interpretation)
    except RuntimeError as error:
        if str(error) == "missing_api_key":
            add_message("assistant", "AI 解读暂未配置好，请稍后再试。卦象已经生成，你可以先从卦辞中想一想此刻最在意的事。")
        else:
            add_message("assistant", "这次暂时没有拿到 AI 解读，但卦象已经为你保留。你不必急着找答案，可以先想一想：眼下你最能掌握的一步是什么？")
    except AuthenticationError:
        add_message("assistant", "AI 解读服务暂时无法验证，请稍后再试。卦象已经生成，不影响你先阅读卦辞。")
    except RateLimitError:
        add_message("assistant", "今天来问的人有点多，AI 解读正在稍作休息。请过一会儿再试，卦象已经为你保留。")
    except APIConnectionError:
        add_message("assistant", "AI 解读暂时连不上，但卦象已经生成。先别急着做决定，想一想：这件事里，你最想守住的是什么？")
    except APIStatusError:
        add_message("assistant", "AI 解读服务暂时忙碌，卦象已经生成。你可以稍后再试，或先从卦辞中寻找一个提醒。")
    except OpenAIError:
        add_message("assistant", "AI 解读暂时不可用，但卦象已经生成。你可以稍后再试。")
    time.sleep(0.1)
   
    add_message("assistant", """感谢使用  
                🥺    
试试作者的 [其他作品](https://kaiyi.cool)   
玩的开心记得点个 star 呀 [网站源代码](https://github.com/RealKai42/liu-yao-divining)     
                """, 0.01)
