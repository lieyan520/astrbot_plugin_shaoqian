import json
import os
import random
import time
from pathlib import Path
from typing import Dict, List, Tuple

# 数据存储路径
DATA_FILE = Path(__file__).parent / "spoon_data.json"
# 抽卡图片文件夹路径（请自行修改为实际路径）
CARD_IMG_FOLDER = Path(__file__).parent / "card_images"
# 确保文件夹存在
CARD_IMG_FOLDER.mkdir(exist_ok=True)

# 初始化数据结构
def init_data() -> Dict:
    """初始化用户数据"""
    default_data = {
        "users": {},  # {user_id: {"spoons": 0, "last_checkin": 0, "last_draw": 0}}
        "version": "1.0.0"
    }
    if not DATA_FILE.exists():
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data
    # 读取现有数据
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        # 数据损坏则重建
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=2)
        return default_data

# 保存数据
def save_data(data: Dict):
    """保存用户数据到JSON文件"""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

# 获取今日日期戳（用于判断每日次数）
def get_today_timestamp() -> int:
    """获取今日0点的时间戳"""
    return int(time.mktime(time.localtime()[:3] + (0, 0, 0, 0, 0, 0)))

# 签到功能核心逻辑
def handle_checkin(user_id: str) -> str:
    """
    处理签到逻辑
    :param user_id: 用户唯一标识
    :return: 签到结果提示语
    """
    data = init_data()
    today = get_today_timestamp()
    
    # 检查今日是否已签到
    user_data = data["users"].get(user_id, {"spoons": 0, "last_checkin": 0, "last_draw": 0})
    if user_data["last_checkin"] == today:
        return f"喂喂喂！你今天已经签到过了！你当本勺是傻子吗！现在你有 {user_data['spoons']} 只勺子~"
    
    # 签到核心逻辑
    success = random.choice([True, False])
    if success:
        # 签到成功：1-5个勺子
        add_spoons = random.randint(1, 5)
        user_data["spoons"] += add_spoons
        result_msg = f"签到成功啦！你获得了 {add_spoons} 只勺子！现在你有 {user_data['spoons']} 只勺子~"
    else:
        # 签到失败：50%真失败，50%慈悲模式
        mercy = random.choice([True, False])
        if mercy:
            user_data["spoons"] += 1
            result_msg = "今天你的运气很差哦~签到失败了~不过本勺大发慈悲！送你一只呐~！获得 1 个安慰勺～现在你有 {user_data['spoons']} 只勺子~"
        else:
            result_msg = "今天你的运气很差哦~签到失败了~现在你有 {user_data['spoons']} 只勺子~"
    
    # 更新签到时间和保存数据
    user_data["last_checkin"] = today
    data["users"][user_id] = user_data
    save_data(data)

# 查询勺子功能
def handle_query(user_id: str) -> str:
    """
    处理勺子查询
    :param user_id: 用户唯一标识
    :return: 查询结果提示语
    """
    data = init_data()
    user_data = data["users"].get(user_id, {"spoons": 0, "last_checkin": 0, "last_draw": 0})
    return f"现在你有 {user_data['spoons']} 只勺子~"

# 排行榜功能
def handle_ranking() -> str:
    """
    生成勺子排行榜（前10）
    :return: 排行榜提示语
    """
    data = init_data()
    users = data["users"]
    
    # 无用户数据
    if not users:
        return "暂无用户数据，快来签到吧！"
    
    # 按勺子数排序（降序）
    sorted_users = sorted(
        users.items(),
        key=lambda x: x[1]["spoons"],
        reverse=True
    )[:10]  # 取前10
    
    # 生成排行榜文本
    ranking_msg = "🥄 勺子排行榜 TOP10 🥄\n"
    for idx, (uid, udata) in enumerate(sorted_users, 1):
        ranking_msg += f"{idx}. 用户{uid}：{udata['spoons']} 只勺子\n"
    
    return ranking_msg.strip()

# 抽卡功能
def handle_draw_card(user_id: str) -> Tuple[bool, str, str]:
    """
    处理抽卡逻辑
    :param user_id: 用户唯一标识
    :return: (是否成功, 提示语, 图片路径)
    """
    data = init_data()
    today = get_today_timestamp()
    
    # 检查今日是否已抽卡
    user_data = data["users"].get(user_id, {"spoons": 0, "last_checkin": 0, "last_draw": 0})
    if user_data["last_draw"] == today:
        return (False, f"你今天已经占卜过了！别想卡bug！本勺可是很聪明的！", "")
    
    # 检查图片文件夹是否有图片
    img_files = [f for f in CARD_IMG_FOLDER.iterdir() if f.suffix.lower() in [".jpg", ".png", ".jpeg", ".gif"]]
    if not img_files:
        return (False, "抽卡失败！卡池为空，请先在 card_images 文件夹中放入图片。", "")
    
    # 随机抽取一张图片
    random_img = random.choice(img_files)
    
    # 更新抽卡时间
    user_data["last_draw"] = today
    data["users"][user_id] = user_data
    save_data(data)
    
    return (True, f"✨让本勺看看你抽到了什么~✨", str(random_img))

# AstrBot插件入口函数（核心）
def astrbot_plugin_main(command: str, user_id: str, *args, **kwargs):
    """
    AstrBot插件主入口
    :param command: 用户发送的指令
    :param user_id: 用户唯一标识（如QQ号/微信号）
    :return: 回复内容（文本/图片）
    """
    # 指令匹配
    if command.strip() == "签到":
        return handle_checkin(user_id)
    elif command.strip() == "勺子查询":
        return handle_query(user_id)
    elif command.strip() == "排行榜":
        return handle_ranking()
    elif command.strip() == "抽卡":
        success, msg, img_path = handle_draw_card(user_id)
        if success:
            # 返回图片+文本（适配AstrBot的返回格式，具体可根据实际框架调整）
            return {
                "type": "image",
                "path": img_path,
                "text": msg
            }
        else:
            return msg
    else:
        # 非插件指令，返回空（交由其他插件处理）
        return None

# 测试代码（可选）
if __name__ == "__main__":
    # 模拟测试
    test_user = "test_user_123"
    
    # 测试签到
    print(handle_checkin(test_user))
    
    # 测试重复签到
    print(handle_checkin(test_user))
    
    # 测试查询
    print(handle_query(test_user))
    
    # 测试排行榜
    print(handle_ranking())
    
    # 测试抽卡（需先在card_images文件夹放图片）
    print(handle_draw_card(test_user))
