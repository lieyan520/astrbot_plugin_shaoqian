import json
import random
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.message_components import Plain, Image
from astrbot.api import logger

DATA_FILE = "data/spoon_sign.json"
IMAGE_FOLDER = "data/spoon_images"

@register("spoon_sign", "你的名字", "勺签插件，每日签到、抽卡、排行榜", "1.0.0")
class SpoonSign(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or {}
        # 数据文件路径
        self.data_file = Path(self.config.get("data_file", DATA_FILE))
        self.data_file.parent.mkdir(parents=True, exist_ok=True)
        self.user_data = self._load_data()

        # 抽卡图片文件夹路径（可通过配置项修改）
        self.image_folder = Path(self.config.get("image_folder", IMAGE_FOLDER))
        self.image_folder.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """插件初始化（可选）"""
        pass

    def _load_data(self) -> Dict[str, Any]:
        """加载用户数据"""
        if self.data_file.exists():
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载数据文件失败: {e}")
                return {}
        return {}

    def _save_data(self):
        """保存用户数据"""
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.user_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存数据文件失败: {e}")

    def _get_user(self, user_id: str) -> dict:
        """获取用户数据，不存在则初始化"""
        if user_id not in self.user_data:
            self.user_data[user_id] = {
                "spoons": 0,
                "last_sign": None,      # 格式 YYYY-MM-DD
                "last_draw": None,      # 格式 YYYY-MM-DD
                "username": ""           # 最近使用的昵称
            }
        return self.user_data[user_id]

    def _update_username(self, user_id: str, username: str):
        """更新用户昵称"""
        user = self._get_user(user_id)
        if username:
            user["username"] = username

    async def _send_result(self, event: AstrMessageEvent, message: str, image_path: Optional[Path] = None):
        """发送消息（可选附带图片）"""
        chain = [Plain(message)]
        if image_path and image_path.exists():
            chain.append(Image.from_file_system_path(str(image_path)))
        await event.send_result(chain)

    @filter.command("签到", alias={"打卡"})
    async def handle_sign(self, event: AstrMessageEvent):
        """处理签到指令"""
        # 获取用户标识（修正：使用 get_sender_id 和 get_sender_name）
        user_id = str(event.get_sender_id())
        username = event.get_sender_name() or "未知用户"
        self._update_username(user_id, username)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        user = self._get_user(user_id)

        # 检查是否已签到
        if user.get("last_sign") == today:
            await self._send_result(event, f"你今天已经签到过了，明天再来吧！当前你有 {user['spoons']} 个勺子。")
            return

        # 签到逻辑
        spoons_gained = 0
        result_msg = ""

        # 第一步：50% 成功 / 50% 失败
        if random.random() < 0.5:  # 成功
            spoons_gained = random.randint(1, 5)
            user["spoons"] += spoons_gained
            result_msg = f"签到成功！获得 {spoons_gained} 个勺子。"
        else:  # 失败
            # 第二步：50% 真正失败 / 50% 慈悲模式
            if random.random() < 0.5:  # 真正失败
                result_msg = "签到失败...下次好运。"
            else:  # 慈悲模式
                spoons_gained = 1
                user["spoons"] += spoons_gained
                result_msg = "签到失败，但触发了慈悲模式！获得 1 个勺子。"

        # 更新最后签到日期
        user["last_sign"] = today
        self._save_data()

        # 最终消息：加上当前勺子总数
        final_msg = f"{result_msg} 当前你有 {user['spoons']} 个勺子。"
        await self._send_result(event, final_msg)

    @filter.command("勺子查询", alias={"查询"})
    async def handle_query(self, event: AstrMessageEvent):
        """查询当前勺子数量"""
        user_id = str(event.get_sender_id())
        username = event.get_sender_name() or ""
        self._update_username(user_id, username)

        user = self._get_user(user_id)
        await self._send_result(event, f"你目前有 {user['spoons']} 个勺子。")

    @filter.command("排行榜")
    async def handle_rank(self, event: AstrMessageEvent):
        """显示勺子持有者前十名"""
        if not self.user_data:
            await self._send_result(event, "目前还没有人拥有勺子～")
            return

        # 按勺子数量降序排序，取前10
        sorted_users = sorted(
            self.user_data.items(),
            key=lambda item: item[1].get("spoons", 0),
            reverse=True
        )[:10]

        lines = ["🏆 勺子排行榜 🏆"]
        for idx, (user_id, data) in enumerate(sorted_users, 1):
            name = data.get("username") or user_id[:4] + "..."  # 显示昵称或截断ID
            spoons = data.get("spoons", 0)
            lines.append(f"{idx}. {name} : {spoons} 个勺子")

        await self._send_result(event, "\n".join(lines))

    @filter.command("抽卡")
    async def handle_draw(self, event: AstrMessageEvent):
        """每日抽卡：随机发送一张图片"""
        user_id = str(event.get_sender_id())
        username = event.get_sender_name() or ""
        self._update_username(user_id, username)

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        user = self._get_user(user_id)

        # 检查是否已抽卡
        if user.get("last_draw") == today:
            await self._send_result(event, f"你今天已经抽过卡了，明天再来吧！当前你有 {user['spoons']} 个勺子。")
            return

        # 检查图片文件夹是否存在且非空
        if not self.image_folder.exists():
            await self._send_result(event, "图片文件夹不存在，请联系管理员。")
            return

        # 获取所有图片文件（常见扩展名）
        image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp')
        images = [f for f in self.image_folder.iterdir() if f.suffix.lower() in image_extensions]

        if not images:
            await self._send_result(event, "图片文件夹中没有可用的图片。")
            return

        # 随机选择一张图片
        chosen = random.choice(images)

        # 更新最后抽卡日期
        user["last_draw"] = today
        self._save_data()

        # 发送图片和提示
        await self._send_result(event, f"✨ 抽卡成功！这是你今天的卡片：", chosen)

    async def terminate(self):
        """插件卸载时保存数据"""
        self._save_data()
