from flask import Flask, request, jsonify
from flask_cors import CORS
import requests
import base64
import io
import os
from PIL import Image, ImageDraw, ImageFilter
import random

app = Flask(__name__)
CORS(app)

# ========== 填你的百度AI密钥 ==========
BAIDU_API_KEY = iorRQUpvBq4WCIrWgA2vh1qL
BAIDU_SECRET_KEY = VGiKpHWVB3GNH5K7ELcSOeSWQepQri

baidu_token = None

# ========== 描述模板库 ==========
DESC_TEMPLATES = {
    "狗": ["忠诚的犬系小精灵，对训练师绝对忠心", "拥有敏锐的嗅觉，能发现隐藏的宝藏", "奔跑速度极快，是战斗中的先锋"],
    "犬": ["来自远古的犬族血脉，威严而可靠", "吼叫声能震慑敌人，降低对方士气"],
    "猫": ["优雅的猫科小精灵，行动悄无声息", "拥有柔软的肉垫，落地无声", "夜晚视力极佳，擅长夜间作战"],
    "喵": ["神秘的喵星人，性格难以捉摸", "撒娇时让人毫无抵抗力，战斗力却爆表"],
    "鸟": ["自由飞翔的鸟类小精灵，速度出众", "拥有锐利的鹰眼，能看穿敌人弱点", "翅膀攻击能掀起狂风"],
    "鸽": ["和平的象征，但战斗时不容小觑", "拥有极强的归巢本能，永远不会迷路"],
    "雀": ["小巧玲珑的雀类精灵，敏捷度MAX", "虽然体型小，但攻击频率极快"],
    "鱼": ["来自深海的鱼类小精灵，水性极佳", "在雨天战斗力会大幅提升"],
    "龟": ["古老的龟族精灵，拥有极高的防御", "坚硬的外壳能抵挡大部分攻击", "寿命极长，见证了无数历史"],
    "兔": ["可爱的兔系精灵，跳跃力惊人", "长耳朵能感知远处的危险", "繁殖能力...我是说闪避能力极强"],
    "鼠": ["机灵的老鼠精灵，擅长寻找食物", "能在极小的空间中穿梭自如", "牙齿锋利，咬合力惊人"],
    "default": ["神秘的野生小精灵，来历不明", "拥有未知的力量，等待训练师发掘", "据说只在特定天气出现"]
}

def get_baidu_token():
    global baidu_token
    if baidu_token:
        return baidu_token
    url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={BAIDU_API_KEY}&client_secret={BAIDU_SECRET_KEY}"
    r = requests.post(url, timeout=10)
    baidu_token = r.json().get("access_token")
    return baidu_token

def recognize_animal(image_b64):
    """百度AI识别动物"""
    try:
        token = get_baidu_token()
        url = f"https://aip.baidubce.com/rest/2.0/image-classify/v1/animal?access_token={token}"
        r = requests.post(url, data={"image": image_b64, "top_num": 1}, 
                         headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
        result = r.json()
        if "result" in result and len(result["result"]) > 0:
            return result["result"][0].get("name", "神秘小精灵")
    except Exception as e:
        print("识别失败:", e)
    return "神秘小精灵"

def cutout_animal(image_b64):
    """百度AI人像分割（对动物也有效）"""
    try:
        token = get_baidu_token()
        url = f"https://aip.baidubce.com/rest/2.0/image-classify/v1/body_seg?access_token={token}"
        r = requests.post(url, data={"image": image_b64}, timeout=15)
        result = r.json()
        if "foreground" in result:
            return base64.b64decode(result["foreground"])
    except Exception as e:
        print("抠图失败:", e)
    return None

def generate_description(animal_name):
    """根据动物名生成描述"""
    for key in DESC_TEMPLATES:
        if key in animal_name:
            return random.choice(DESC_TEMPLATES[key])
    return random.choice(DESC_TEMPLATES["default"])

def create_card_image(cutout_bytes, rarity):
    """合成卡牌图片"""
    try:
        # 打开抠图
        img = Image.open(io.BytesIO(cutout_bytes)).convert("RGBA")
        
        # 缩放适配
        img.thumbnail((380, 380), Image.Resampling.LANCZOS)
        
        # 创建卡牌背景（根据稀有度）
        if rarity == "传说":
            bg = Image.new('RGBA', (500, 500), (255, 215, 0, 255))
            border_color = (255, 255, 255, 255)
        elif rarity == "史诗":
            bg = Image.new('RGBA', (500, 500), (139, 90, 150, 255))
            border_color = (200, 160, 216, 255)
        elif rarity == "稀有":
            bg = Image.new('RGBA', (500, 500), (90, 122, 150, 255))
            border_color = (155, 183, 203, 255)
        else:
            bg = Image.new('RGBA', (500, 500), (107, 101, 96, 255))
            border_color = (160, 154, 148, 255)
        
        # 画圆角边框
        draw = ImageDraw.Draw(bg)
        draw.rounded_rectangle([10, 10, 490, 490], radius=30, outline=border_color, width=8)
        
        # 居中粘贴抠图
        cx = (500 - img.width) // 2
        cy = (500 - img.height) // 2
        bg.paste(img, (cx, cy), img)
        
        # 保存为base64
        buffer = io.BytesIO()
        bg.save(buffer, format="PNG")
        return base64.b64encode(buffer.getvalue()).decode()
    except Exception as e:
        print("合成失败:", e)
        return None

@app.route("/api/process", methods=["POST"])
def process():
    try:
        file = request.files.get("image")
        if not file:
            return jsonify({"error": "没有图片"}), 400
        
        image_bytes = file.read()
        image_b64 = base64.b64encode(image_bytes).decode()
        
        # 1. 识别动物
        animal_name = recognize_animal(image_b64)
        
        # 2. 抠图
        cutout_bytes = cutout_animal(image_b64)
        
        # 3. 生成描述
        description = generate_description(animal_name)
        
        # 4. 合成卡牌（先用普通背景，小程序再根据实际稀有度套壳）
        card_base64 = None
        if cutout_bytes:
            card_base64 = create_card_image(cutout_bytes, "普通")
        
        return jsonify({
            "success": True,
            "animal": animal_name,
            "description": description,
            "cutout_base64": base64.b64encode(cutout_bytes).decode() if cutout_bytes else None,
            "card_base64": card_base64
        })
        
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

@app.route("/")
def index():
    return "小精灵卡牌后端服务运行中！"

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
