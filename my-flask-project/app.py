import os
import requests
from flask import Flask, request, redirect, session, jsonify
from datetime import datetime, timedelta
import uuid
import json

app = Flask(__name__)
app.secret_key = str(uuid.uuid4())  # 生成随机密钥用于session

# ================= 配置区域 =================
# 1. 优先从环境变量读取（安全），如果没有则使用默认值（方便本地调试）
CORP_ID = os.environ.get("CORP_ID", "ww122e71f4c8e0fd1b")
APP_SECRET = os.environ.get("APP_SECRET", "tCpJb6DdCT3UsQKp1TsGQZP0u6Kvpdxei58qffT5WUQ")
AGENT_ID = os.environ.get("AGENT_ID", "1000003")  # 保持字符串类型
# 企业微信OAuth2.0配置
REDIRECT_HOST = os.environ.get("REDIRECT_HOST", "https://testschedule.ncu.edu.cn")  # 使用企业微信配置的域名
OAUTH2_CALLBACK = f"{REDIRECT_HOST}/oauth_callback"
OAUTH2_SCOPE = "snsapi_privateinfo"  # 获取用户信息需要这个scope
# ===========================================

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={APP_SECRET}"
    r = requests.get(url).json()
    if r['errcode'] == 0: 
        print(f"获取access_token成功: {r['access_token'][:10]}...")  # 调试信息
        return r['access_token']
    raise Exception(f"Token获取失败: {r.get('errmsg', '未知错误')}")

def get_next_week_timestamp(weekday, time_str):
    now = datetime.now()
    target_weekday_py = weekday - 1
    days_ahead = target_weekday_py - now.weekday()
    if days_ahead <= 0: days_ahead += 7
    target_date = now + timedelta(days=days_ahead)
    time_parts = time_str.split(":")
    target_dt = target_date.replace(hour=int(time_parts[0]), minute=int(time_parts[1]), second=0)
    return int(target_dt.timestamp())

# CSS样式模板（避免与格式化冲突）
STYLE_CSS = '''
<style>body{font-family:sans-serif; text-align:center; padding:20px; background-color:#f6f6f6;} .container{background:white; padding:20px; border-radius:10px; margin-top:50px;} h1{color:#333; font-size:20px;} p{color:#666; font-size:14px;} .btn{display:inline-block; background-color:#07C160; color:white; padding:15px 40px; text-decoration:none; border-radius:8px; font-size:18px; margin-top:20px; border:none;}</style>
'''

@app.route('/')
def index():
    # 检查用户是否已授权
    if 'user_id' not in session:
        # 生成state参数防止CSRF攻击
        state = str(uuid.uuid4())
        session['oauth2_state'] = state
        # 构造OAuth2.0授权URL
        oauth_url = (
            f"https://open.weixin.qq.com/connect/oauth2/authorize?"
            f"appid={CORP_ID}&redirect_uri={OAUTH2_CALLBACK}&response_type=code&scope={OAUTH2_SCOPE}&state={state}#wechat_redirect"
        )
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>课表同步</title>
        {STYLE_CSS}
        </head>
        <body><div class="container"><h1>📅 课表同步助手</h1><p>请先授权登录，然后同步课程到日程</p><a href="{oauth_url}" class="btn">授权登录</a></div></body>
        </html>
        '''
    else:
        return f'''
        <!DOCTYPE html>
        <html>
        <head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>课表同步</title>
        {STYLE_CSS}
        </head>
        <body><div class="container"><h1>📅 课表同步助手</h1><p>已授权用户: {session.get('user_name', '未知用户')}</p><a href="/do_sync" class="btn">一键同步日程</a></div></body>
        </html>
        '''

@app.route('/oauth_callback')
def oauth_callback():
    # 获取授权code和state
    code = request.args.get('code')
    state = request.args.get('state')
    
    # 验证state防止CSRF攻击
    if state != session.get('oauth2_state'):
        return "❌ 授权失败：无效的state参数"
    
    try:
        # 获取access_token
        token = get_access_token()
        print(f"使用token: {token[:10]}...")  # 调试信息
        
        # 获取用户信息
        token_url = f"https://qyapi.weixin.qq.com/cgi-bin/user/getuserinfo?access_token={token}&code={code}&agentid={AGENT_ID}"
        resp = requests.get(token_url).json()
        print(f"getuserinfo响应: {json.dumps(resp, indent=2)}")  # 调试信息
        
        if resp['errcode'] == 0:
            # 获取用户信息
            user_id = resp['UserId']
            user_name = resp.get('UserName', '未知用户')
            
            # 存储用户信息到session
            session['user_id'] = user_id
            session['user_name'] = user_name
            
            return redirect('/')
        else:
            return f"❌ 授权失败: {resp.get('errmsg', '未知错误')}"
    except Exception as e:
        return f"❌ 授权异常: {str(e)}"

@app.route('/do_sync')
def do_sync():
    # 检查用户是否已授权
    if 'user_id' not in session:
        return redirect('/')
    
    try:
        token = get_access_token()
        print(f"使用token: {token[:10]}...")  # 调试信息
        
        url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/schedule/add?access_token={token}"

        # 这里可以接入数据库或表单获取真实课程数据
        # 模拟课程数据
        mock_data = {
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
                "attendees": [{ "userid": session['user_id'] }]  # 使用session中的用户ID
            },
            "agentid": AGENT_ID  # 确保agentid为字符串
        }

        print(f"发送的请求数据: {json.dumps(data, indent=2)}")  # 调试信息
        
        resp = requests.post(url, json=data).json()
        print(f"schedule/add响应: {json.dumps(resp, indent=2)}")  # 调试信息

        if resp['errcode'] == 0:
            return '<html><body style="text-align:center; padding:50px;"><h2 style="color:green;">✅ 同步成功！</h2><p>请打开企业微信日历查看。</p><a href="/">返回首页</a></body></html>'
        else:
            return f"❌ 同步失败: {resp.get('errmsg', '未知错误')}"

    except Exception as e:
        return f"⚠️ 服务器错误: {str(e)}"

# ================= 启动配置 =================
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))  # 云托管默认使用80端口
    app.run(host="0.0.0.0", port=port, debug=True)
