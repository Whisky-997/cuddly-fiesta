import os
import requests
from flask import Flask, request, redirect, session
from datetime import datetime, timedelta
from urllib.parse import urlencode

app = Flask(__name__)
# 随机设置一个 secret_key 用于 session；生产环境建议改为固定且安全的字符串
app.secret_key = os.urandom(24)

# ================= 配置区域 =================
CORP_ID = os.environ.get("CORP_ID", "ww122e71f4c8e0fd1b")
APP_SECRET = os.environ.get("APP_SECRET", "tCpJb6DdCT3UsQKp1TsGQZP0u6Kvpdxei58qffT5WUQ")
AGENT_ID = int(os.environ.get("AGENT_ID", "1000003"))

# 重要：回调地址的域名必须在企微后台的可信域名/授权回调域中配置
REDIRECT_HOST = os.environ.get("REDIRECT_HOST", "https://testschedule.ncu.edu.cn")  # 请改成你的域名
# ===========================================

def get_access_token():
    url = f"https://qyapi.weixin.qq.com/cgi-bin/gettoken?corpid={CORP_ID}&corpsecret={APP_SECRET}"
    r = requests.get(url).json()
    if r['errcode'] == 0:
        return r['access_token']
    raise Exception(f"Token获取失败: {r}")

def get_next_week_timestamp(weekday, time_str):
    now = datetime.now()
    target_weekday_py = weekday - 1
    days_ahead = target_weekday_py - now.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    target_date = now + timedelta(days=days_ahead)
    hour, minute = map(int, time_str.split(":"))
    target_dt = target_date.replace(hour=hour, minute=minute, second=0, microsecond=0)
    return int(target_dt.timestamp())

@app.route('/')
def index():
    return '''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>课表同步</title>
        <style>
            body{font-family:sans-serif; text-align:center; padding:20px; background-color:#f6f6f6;}
            .container{background:white; padding:20px; border-radius:10px; margin-top:50px;}
            h1{color:#333; font-size:20px;}
            p{color:#666; font-size:14px;}
            .btn{display:inline-block; background-color:#07C160; color:white; padding:15px 40px; text-decoration:none; border-radius:8px; font-size:18px; margin-top:20px; border:none;}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📅 课表同步助手</h1>
            <p>点击下方按钮，以你的身份自动将下周课程加入日程</p>
            <a href="/auth_url" class="btn">一键同步日程</a>
        </div>
    </body>
    </html>
    '''

# 新增：构造企微 OAuth2 授权链接
@app.route('/auth_url')
def auth_url():
    from urllib.parse import quote
    # 回调地址：授权完成后企微会跳转到这里，并带上 code 与 state
    redirect_uri = quote(f"{REDIRECT_HOST}/oauth_callback", safe='')
    # 使用 snsapi_privateinfo 以便获取姓名；需要在企微后台为应用开启相关敏感信息权限
    scope = "snsapi_privateinfo"
    state = os.urandom(8).hex()  # 简单的随机字符串，防止 CSRF
    session['oauth_state'] = state

    params = {
        "appid": CORP_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": scope,
        "agentid": AGENT_ID,
        "state": state
    }
    base = "https://open.weixin.qq.com/connect/oauth2/authorize"
    url = f"{base}?{urlencode(params)}#wechat_redirect"
    return redirect(url)

# 新增：OAuth2 回调处理
@app.route('/oauth_callback')
def oauth_callback():
    try:
        # 校验 state，防止 CSRF
        state = request.args.get('state')
        if state != session.pop('oauth_state', None):
            return "❌ 状态校验失败，请求非法。"
        code = request.args.get('code')
        if not code:
            return "❌ 未获取到授权码。"

        token = get_access_token()

        # 1) 用 code 换取用户身份（含 userid 与 user_ticket）
        userinfo_url = f"https://qyapi.weixin.qq.com/cgi-bin/auth/getuserinfo?access_token={token}&code={code}"
        userinfo_resp = requests.get(userinfo_url).json()
        if userinfo_resp.get('errcode') != 0:
            return f"❌ 获取用户身份失败: {userinfo_resp.get('errmsg')}"
        userid = userinfo_resp.get('userid')
        user_ticket = userinfo_resp.get('user_ticket')
        name = ""
        if user_ticket:
            # 2) 用 user_ticket 获取用户详情（含姓名）
            detail_url = f"https://qyapi.weixin.qq.com/cgi-bin/auth/getuserdetail?access_token={token}"
            detail_resp = requests.post(detail_url, json={"user_ticket": user_ticket}).json()
            if detail_resp.get('errcode') == 0:
                name = detail_resp.get('name', "")

        # 如果未获取到姓名，至少使用 userid
        display_name = name if name else userid

        # 3) 创建日程（以当前用户为参与者）
        add_url = f"https://qyapi.weixin.qq.com/cgi-bin/oa/schedule/add?access_token={token}"
        start_ts = get_next_week_timestamp(1, "08:00")
        end_ts = get_next_week_timestamp(1, "09:35")

        body = {
            "schedule": {
                "summary": f"测试日程 - {display_name}",
                "description": "这是一条测试日程，来自课表同步助手。",
                "start_time": start_ts,
                "end_time": end_ts,
                "location": "前湖北校区研究生院103",
                "reminders": {"is_remind": 1, "remind_before_event_secs": 900},
                "attendees": [{"userid": userid}]
            },
            "agentid": AGENT_ID
        }
        add_resp = requests.post(add_url, json=body).json()
        if add_resp.get('errcode') == 0:
            return f'<html><body style="text-align:center; padding:50px;"><h2 style="color:green;">✅ 同步成功！</h2><p>已为 {display_name} 创建下周的测试日程，请打开企业微信日历查看。</p><a href="/">返回首页</a></body></html>'
        else:
            return f"❌ 日程创建失败: {add_resp.get('errmsg')}"
    except Exception as e:
        return f"⚠️ 服务器错误: {str(e)}"

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 80))
    app.run(host="0.0.0.0", port=port, debug=True)
