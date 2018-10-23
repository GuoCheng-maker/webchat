from django.shortcuts import render,HttpResponse
import requests
import time
import re
import json

CTIME=None
QCODE=None
TIP=1
TICKET_DICT={}
ALL_COOKIES={}
USER_INIT_DICT = {}
def login(request):
    '''
    获取动态二维码，并在我们自己的网站展示出来。
    :param request:
    :return:
    '''
    global CTIME
    CTIME=time.time()
    response=requests.get(
        url="https://login.wx.qq.com/jslogin?appid=wx782c26e4c19acffb&fun=new&lang=zh_CN&_=%s"%CTIME,
    )
    # print(response.text)
    qcode=re.findall('uuid = "(.*)";',response.text)
    # window.QRLogin.code = 200; window.QRLogin.uuid = "gc79K_9xeg==";
    global QCODE
    QCODE = qcode[0]
    return render(request,"login.html",{"qcode":QCODE})

def check_login(request):
    '''
    监听用户是否已经扫码
    并且需要监听用户是否已经点击确认
    :param request:
    :return:
    '''
    global TIP
    global QCODE
    ret={'code':408,'data':None}
    r1=requests.get(
        url='https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login?loginicon=true&uuid=%s&tip=%s&r=-1096266450&_=%s'%(QCODE,TIP,CTIME,)
    )
    ALL_COOKIES.update(r1.cookies.get_dict())
    # print(r1.text)
    if 'window.code=408' in r1.text:
        print("无人扫码")
        return HttpResponse(json.dumps(ret))

    elif 'window.code=201' in r1.text:
        ret['code']=201
        avatar = re.findall("window.userAvatar = '(.*)';", r1.text)
        ret['data']=avatar
        TIP=0
        return HttpResponse(json.dumps(ret))

    elif 'window.code=200' in r1.text:
        #用户点击确认，初始化信息。
        redirect_uri=re.findall('window.redirect_uri="(.*)";',r1.text)[0]
        #做一个字符串的拼接
        redirect_uri=redirect_uri+"&fun=new&version=v2"

        ##################获取凭证####################
        r2=requests.get(url=redirect_uri)
        ALL_COOKIES.update(r2.cookies.get_dict())
        # print(r2.text)
        print("用户点击确认登录")
        from bs4 import BeautifulSoup
        soup=BeautifulSoup(r2.text,'html.parser')
        for tag in soup.find('error').children:
            TICKET_DICT[tag.name]=tag.get_text()
        # print(ticket_dit)
        ret['code']=200
        return HttpResponse(json.dumps(ret))

def user(request):
    #################获取用户信息###################
    get_user_dict = {
        "BaseRequest": {
            'DeviceID': "e669318666283110",
            'Sid': TICKET_DICT['wxsid'],
            'Skey': TICKET_DICT['skey'],
            'Uin': TICKET_DICT['wxuin'],
        }
    }
    get_user_url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit?r=-1101270131&lang=zh_CN&pass_ticket=' +TICKET_DICT["pass_ticket"]
    # requests.get(url=get_user_url)

    r3 = requests.post(
        url=get_user_url,
        json=get_user_dict
    )
    r3.encoding = 'utf8'
    ALL_COOKIES.update(r3.cookies.get_dict())
    user_init_dict = json.loads(r3.text)

    # 将字典写入本地
    f = open('log', mode='w+', encoding='utf-8')
    f.write(str(user_init_dict))
    f.close()

    USER_INIT_DICT.update(user_init_dict)
    import pprint
    pprint.pprint(user_init_dict)

    return render(request,"user.html",{"user_init_dict":user_init_dict})

def contact_list(request):
    ctime=str(time.time())
    base_url='https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact?lang=zh_CN&pass_ticket=%s&r=%s&seq=0&skey=%s'
    url=base_url%(TICKET_DICT['pass_ticket'],ctime,TICKET_DICT['skey'])
    response=requests.get(url=url,cookies=ALL_COOKIES)
    response.encoding="utf-8"
    contact_list_dict=json.loads(response.text)
    return render(request,"contact_list.html",{"contact_list_dict":contact_list_dict})


def send_msg(request):
    msg=request.GET.get("msg")
    to_user=request.GET.get("toUser")
    url = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsendmsg?lang=zh_CN&pass_ticket=%s' % (TICKET_DICT['pass_ticket'],)
    ctime=time.time()
    post_dict = {
        'BaseRequest': {
            'DeviceID': "e402310790089148",
            'Sid': TICKET_DICT['wxsid'],
            'Uin': TICKET_DICT['wxuin'],
            'Skey': TICKET_DICT['skey'],
        },
        "Msg": {
            'ClientMsgId': ctime,
            'Content': msg,
            'FromUserName': USER_INIT_DICT['User']['UserName'],
            'LocalID': ctime,
            'ToUserName': to_user.strip(),
            'Type': 1
        },
        'Scene': 0
    }
    response=requests.post(url=url,data=bytes(json.dumps(post_dict,ensure_ascii=False),encoding="utf-8"))
    print(response)
    return HttpResponse("ok")

def get_msg(request):
    print("staring......")
    synckey_list=USER_INIT_DICT['SyncKey']['List']
    sync_list=[]
    for item in synckey_list:
        temp = "%s_%s"%(item['Key'],item['Val'],)
        sync_list.append(temp)
    synckey="|".join(sync_list)

    r1=requests.get(
        url="https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck",
        params={
            'r': time.time(),
            'skey': TICKET_DICT['skey'],
            'sid': TICKET_DICT['wxsid'],
            'uin': TICKET_DICT['wxuin'],
            'deviceid': "e669318666283110",
            'synckey': synckey
        },
        cookies=ALL_COOKIES
    )
    if 'retcode:"0",selector:"2"' in r1.text:
        post_dict = {
            'BaseRequest': {
                'DeviceID': "e402310790089148",
                'Sid': TICKET_DICT['wxsid'],
                'Uin': TICKET_DICT['wxuin'],
                'Skey': TICKET_DICT['skey'],
            },
            "SyncKey":USER_INIT_DICT['SyncKey'],
            'rr':1
        }
        r2=requests.post(
            url='https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync',
            params={
                'skey': TICKET_DICT['skey'],
                'sid': TICKET_DICT['wxsid'],
                'pass_ticket': TICKET_DICT['pass_ticket'],
                'lang': 'zh_CN'
            },
            json=post_dict
        )
        r2.encoding='utf-8'
        msg_dict=json.loads(r2.text)
        for msg_info in msg_dict["AddMsgList"]:
            print(msg_info['Content'])

        USER_INIT_DICT['SyncKey'] = msg_dict['SyncKey']
        print(r1.text)
        print("ending......")
        return HttpResponse('...')