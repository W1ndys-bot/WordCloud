# script/WordCloud/main.py

import logging
import os
import sys
import jieba
from datetime import datetime
from wordcloud import WordCloud
import base64
import sqlite3

# 添加项目根目录到sys.path
sys.path.append(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)

from app.config import owner_id
from app.api import *
from app.switch import load_switch, save_switch

# 数据存储路径，实际开发时，请将WordCloud替换为具体的数据存放路径
DATA_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "data",
    "WordCloud",
)


# 查看功能开关状态
def load_function_status(group_id):
    try:
        return load_switch(group_id, "词云统计")
    except Exception as e:
        logging.error(f"加载功能状态失败: {e}")
        return None


# 保存功能开关状态
def save_function_status(group_id, status):
    try:
        save_switch(group_id, "词云统计", status)
    except Exception as e:
        logging.error(f"保存功能状态失败: {e}")


# 初始化文件
def init_db(group_id):
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")
        db_path = os.path.join(DATA_DIR, f"{date_str}_{group_id}.db")
        os.makedirs(DATA_DIR, exist_ok=True)
        if not os.path.exists(db_path):
            with sqlite3.connect(db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("CREATE TABLE IF NOT EXISTS wordcloud (word TEXT)")
                conn.commit()
                logging.info(f"初始化数据库 {db_path}")
                return True
        else:
            return False
    except Exception as e:
        logging.error(f"初始化数据库失败: {e}")
        return False


# 存储分词
def add_wordcloud_data(group_id, text):
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")
        db_path = os.path.join(DATA_DIR, f"{date_str}_{group_id}.db")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO wordcloud (word) VALUES (?)", (text,))
            conn.commit()
    except Exception as e:
        logging.error(f"存储分词数据失败: {e}")


# 获取数据库中的数据
def get_wordcloud_data(group_id):
    try:
        date_str = datetime.now().strftime("%Y_%m_%d")
        db_path = os.path.join(DATA_DIR, f"{date_str}_{group_id}.db")
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT word FROM wordcloud")
            return cursor.fetchall()
    except Exception as e:
        logging.error(f"获取词云数据失败: {e}")
        return []


# 绘制词云图片
def draw_wordcloud(group_id):
    try:
        data = get_wordcloud_data(group_id)

        # logging.info(f"词云数据: {data}")

        # 合并所有文本
        combined_text = " ".join(word_tuple[0] for word_tuple in data)

        logging.info(f"合并后文本: {combined_text}")

        # 使用jieba分词
        combined_text = " ".join(jieba.lcut(combined_text))

        logging.info(f"分词后文本: {combined_text}")

        # 生成词云
        wordcloud = WordCloud(
            font_path="/usr/local/lib/python3.10/dist-packages/matplotlib/mpl-data/fonts/ttf/SIMHEI.TTF",
            width=900,
            height=900,
            background_color="white",
        ).generate(combined_text)

        # 将词云图像保存到字节流
        from io import BytesIO

        image_stream = BytesIO()
        wordcloud.to_image().save(image_stream, format="PNG")
        image_stream.seek(0)

        # 将字节流转换为base64编码
        encoded_string = base64.b64encode(image_stream.read()).decode("utf-8")
        # logging.info(f"词云图像base64: {encoded_string}")
        encoded_string = f"base64://{encoded_string}"
        return encoded_string
    except Exception as e:
        logging.error(f"绘制词云失败: {e}")
        return ""


# 提取消息中的文本
def extract_text_from_message(message):
    try:
        text = ""
        for item in message:
            if item.get("type") == "text":
                text += item.get("data", {}).get("text", "")
        return text
    except Exception as e:
        logging.error(f"提取消息文本失败: {e}")
        return ""


# 群消息处理函数
async def handle_WordCloud_group_message(websocket, msg):
    # 确保数据目录存在
    os.makedirs(DATA_DIR, exist_ok=True)

    try:
        user_id = str(msg.get("user_id"))
        group_id = str(msg.get("group_id"))
        role = str(msg.get("sender", {}).get("role"))
        message_id = str(msg.get("message_id"))
        message = msg.get("message")
        raw_message = msg.get("raw_message")

        # 初始化数据库
        init_db(group_id)

        # 处理开关命令
        if raw_message == "wcon":
            if load_function_status(group_id):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]【+】词云统计已经开启了，无需重复开启",
                )
            else:
                save_function_status(group_id, True)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]【+】词云统计已开启",
                )
            return True  # 确保处理完命令后返回

        elif raw_message == "wcoff":
            if not load_function_status(group_id):
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]【+】词云统计已关闭，无需重复关闭",
                )
            else:
                save_function_status(group_id, False)
                await send_group_msg(
                    websocket,
                    group_id,
                    f"[CQ:reply,id={message_id}]【+】词云统计已关闭",
                )
            return True  # 确保处理完命令后返回

        if raw_message == "今日词云":

            await send_group_msg(websocket, group_id, "【+】词云图绘制中...")
            encoded_string = draw_wordcloud(group_id)
            message = f"[CQ:reply,id={message_id}][CQ:image,file={encoded_string}]"
            await send_group_msg(websocket, group_id, message)
            return

        if load_function_status(group_id):
            # 提取消息中的文本
            text = extract_text_from_message(message)
            if text:
                add_wordcloud_data(group_id, text)

    except Exception as e:
        logging.error(f"处理WordCloud群消息失败: {e}")
        return


# 定时任务
async def wordcloud_task(websocket):
    try:
        # 今日日期
        today = datetime.now().strftime("%Y_%m_%d")
        # 时间是否是每天最后一分钟
        if datetime.now().strftime("%H:%M") == "23:59":
            # 遍历目录下所有文件
            for file in os.listdir(DATA_DIR):
                if file.startswith(today):
                    group_id = file.split("_")[3]
                    encoded_string = draw_wordcloud(group_id)
                    message = f"叮咚~这是群{group_id}在{today}的词云图[CQ:image,file={encoded_string}]"
                    await send_group_msg(websocket, group_id, message)

    except Exception as e:
        logging.error(f"词云定时任务失败: {e}")