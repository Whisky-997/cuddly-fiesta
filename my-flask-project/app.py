import os
import requests
from flask import Flask, request
from datetime import datetime, timedelta

app = Flask(__name__)

# ================= 配置区域 =================
# 1. 优先从环境变量读取（安全），如果没有则使用默认值（方便本地调试）
CORP_ID = os.environ.get("CORP_ID", "ww122e71f4c8e0fd1b")
APP_SECRET = os.environ.get("APP_SECRET", "tCpJb6DdCT3UsQKp1TsGQZP0u6Kvpdxei58qffT5WUQ")
AGENT_ID = int(os.environ.get("AGENT_ID", "1000003"))
# ===========================================

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={APP_SECRET}"
    r = requests.get(url).json()
    if r['errcode'] == 0: return r['access_token']
    raise Exception("Token获取失败")

def get_next_week_timestamp(weekday, time_str):
    now = datetime.now()
    target_weekday_py = weekday - 1
    days_ahead = target_weekday_py - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    target_date = now + timedelta(days=days_ahead)
    time_parts = time_str.split(":")
    target_dt = target_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]), second=0)
    return int(target_dt.timestamp())

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>课表同步</title>
    <style>body{font-family:sans-serif; text-align:center; padding:20px; background-color:#f6f6f6;} .container{background:white; padding:20px; border-radius:10px; margin-top:50px;} h1{color:#333; font-size:20px;} p{color:#666; font-size:14px;} .btn{display:inline-block; background-color:#07C160; color:white; padding:15px 40px; text-decoration:none; border-radius:8px; font-size:18px; margin-top:20px; border:none;}</style>
    </head>
    <body><div class="container"><h1>📅 课表同步助手</h1><p>点击下方按钮，自动将下周课程加入日程</p><a href="/do_sync" class="btn">一键同步日程</a></div></body>
    </html>
    '''

@app.route('/do_sync')
def do_sync():
    try:
        token = get_access_token()
        url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/schedule/add?access_token={token}"

        # 这里的数据你可以后续接入数据库或表单
        mock_data = {
            "student_id": "YangZhengJun", # 【重要】记得改成你的企业微信ID
            "course_name": "网络取证",
            "location": "前湖北校区研究生院103",
            "teacher": "黎鹰",
            "weekday": 1,
            "start_time_str": "08:00",
            "end_time_str": "09:35"
        }

        start_ts = get_next_week_timestamp(mock_data['weekday'], mock_data['start_time_str'])
        end_ts = get_next_week_timestamp(mock_data['weekday'], mock_data['end_time_str'])

        data = {
            "schedule": {
                "summary": f"{mock_data['course_name']} - {mock_data['teacher']}",
                "start_time": start_ts,
                "end_time": end_ts,
                "location": mock_data['location'],
                "reminders": { "is_remind": 1, "remind_before_event_secs": 900 },
                "attendees": [{ "userid": mock_data['student_id'] }]
            },
            "agentid": AGENT_ID
        }

        resp = requests.post(url, json=data).json()

        if resp['errcode'] == 0:
            return '<html><body style="text-align:center; padding:50px;"><h2 style="color:green;">✅ 同步成功！</h2><p>请打开企业微信日历查看。</p><a href="/">返回首页</a></body></html>'
        else:
            return f"❌ 同步失败: {resp['errmsg']}"

    except Exception as e:
        return f"⚠️ 服务器错误: {str(e)}"

# ================= 启动配置 =================
# 云托管环境会自动分配端口，通过环境变量 PORT 传入
# 本地调试时默认使用 5000
if __name__ == "__main__":
    # 从环境变量读取端口，默认5000（本地调试用）
    port = int(os.environ.get("PORT", 80))
    # 必须监听0.0.0.0，否则云托管无法访问
    app.run(host="0.0.0.0", port=port, debug=True)
