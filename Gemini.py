import re
import sys
import time
import json
import random
import markdown
import datetime
import requests
import threading
import webbrowser
from PyQt6.QtGui import *
from PyQt6.QtCore import *
from PyQt6.QtWidgets import *
from functools import partial
import google.generativeai as genai

ml=[]
config=None
VERSION=1.50
qt_newversion=None
qt_lasttime=None
m_width=None
m_height=None
find_radius=re.compile(r'border-radius:(.*?)px')
find_text=re.compile(r'text: "(.*?)"')

def getcolor():
    rgb=(random.randint(0,255),random.randint(0,255),random.randint(0,255))
    color="#"+"".join(["{:02x}".format(value) for value in rgb])
    return color

class RwConfig:
    def __init__(self):
        try:
            with open('config.json') as f:
                global config
                config=json.load(f)
        except FileNotFoundError:
            MessageBox('配置文件不存在或路径错误!')
        except json.decoder.JSONDecodeError:
            MessageBox('配置文件不是有效的JSON格式!')
        except PermissionError:
            MessageBox('没有足够权限读取或写入配置文件!')
    def wconfig(self,zone,name,value):
        try:
            with open('config.json','w') as f:
                config[zone][name]=value
                json.dump(config,f,indent=4)
        except PermissionError:
            MessageBox('没有足够权限读取或写入配置文件!')

rwconfig=RwConfig()
blopen=config['blur']['open']
blradius=config['blur']['blur_radius']

bgcolor=config['window']['bg_color']
bgtheme=config['window']['theme']
qradius=config['window']['q_radius']
aradius=config['window']['a_radius']

dnopen=config['dynamic']['open']
dnspeed=config['dynamic']['speed']
dncurve=config['dynamic']['curve']

interval=config['update']['interval']
lasttime=datetime.datetime.strptime(config['update']['lasttime'],'%Y-%m-%d %H:%M:%S')

class MessageBox(QObject):
    messageSignal=pyqtSignal(str)
    connection=None
    def connectshow(self,slot):
        if self.connection is not None:self.messageSignal.disconnect(self.connection)
        self.connection=self.messageSignal.connect(slot)
    @pyqtSlot(str)
    def show(self,msg='测试',tittle='警告',level='QMessageBox.Icon.Warning',url=None,open=False):
        messagebox=QMessageBox()
        messagebox.setWindowIcon(QIcon('images/warm.png'))
        messagebox.setIcon(eval(level))
        messagebox.setWindowTitle(tittle)
        messagebox.setText(msg)
        messagebox.accepted.connect(lambda:self.onAccepted(url,open))
        messagebox.exec()
    def onAccepted(self,url,open):
        if open:webbrowser.open(url)

messagebox=MessageBox()

class CheckUpdate:
    def __init__(self):
        super().__init__()
        self.desc=None
        self.url=None
    def check(self,skip=False):
        if skip:
            self.checkUpdate()
            return
        a=datetime.datetime.now()
        b=lasttime+datetime.timedelta(days=int(interval))
        if a<b:return
        self.checkUpdate()
    def checkUpdate(self):
        global lasttime
        try:
            data=self.get_data()  
            new_version=data["version"]
            if VERSION<new_version:
                    self.desc=data["desc"]
                    self.url=data["url"]
                    messagebox.connectshow(partial(messagebox.show,'当前版本:'+str(VERSION)+'\n云端版本:'+str(new_version)+'\n更新说明:'+self.desc+'\n更新地址:'+self.url+'\n点击OK将跳转下载','检测到更新','QMessageBox.Icon.Information',self.url,True))
            else:
                messagebox.connectshow(partial(messagebox.show,'当前已是最新版本','通知','QMessageBox.Icon.Information'))
            rwconfig.wconfig('update','lasttime',datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            lasttime=config['update']['lasttime']
            qt_newversion.setText('云端版本:'+str(checkupdate.get_data()['version']))
            qt_lasttime.setText('检查时间:'+lasttime)
        except Exception as e:
            messagebox.connectshow(partial(messagebox.show,f'原因:\n{type(e).__name__}:{e}','检查更新失败','QMessageBox.Icon.Warning'))
        messagebox.messageSignal.emit('signal')
    def get_data(self):
        try:
            url="https://raw.githubusercontent.com/xiyi20/GeminiGui/main/update.json"
            response=requests.get(url)
            data=response.json()
            return data
        except Exception as e:
            messagebox.connectshow(partial(messagebox.show,f'原因:\n{type(e).__name__}:{e}','检查更新失败','QMessageBox.Icon.Warning'))
            messagebox.messageSignal.emit('signal')
            return None

checkupdate=CheckUpdate()

class Gemini:
    def __init__(self):
        genai.configure(api_key="AIzaSyCYbTJdgdMy5ETlRFPAcpQozMrnYLp5g0w",transport='rest')
        # Set up the model
        generation_config={
            "temperature": 0.9,
            "top_p": 1,
            "top_k": 1,
            "max_output_tokens": 2048,
        }
        safety_settings=[
            {
                "category": "HARM_CATEGORY_HARASSMENT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_HATE_SPEECH",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "threshold": "BLOCK_NONE"
            },
            {
                "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                "threshold": "BLOCK_NONE"
            },
        ]
        self.model=genai.GenerativeModel(model_name="gemini-pro",
                                           generation_config=generation_config,
                                           safety_settings=safety_settings)
        self.chat=self.model.start_chat(history=[])

    def get_content(self,code,question):
        try:
            response=self.chat.send_message(question).text
            if code==0:
                response=markdown.markdown(response)
            return response
        except Exception as e:
            return f'{type(e).__name__}:{e}'
            # messagebox.messageSignal.connect(messagebox.show)
            # messagebox.messageSignal.emit(f'{type(e).__name__}:{e}')

class BlurredLabel(QLabel):
    def __init__(self,parent=None,items=[]):
        super().__init__(parent)
        global ml
        self.setGeometry(0,0,parent.width(),parent.height())
        for item in items:
            type=item.get('type',11)
            color=item.get('color','red')
            last_time=item.get('last_time',3)
            shape=item.get('shape',1)
            ml.append(MoveLabel(self,type=type,color=color,last_time=last_time,shape=shape))
        self.blur(blopen,blradius)
    def blur(self,state,num):
        if state==0:
            blur_effect=QGraphicsBlurEffect()
            blur_effect.setBlurRadius(num)
            self.setGraphicsEffect(blur_effect)
        else:
            self.setGraphicsEffect(None)

class MoveLabel(QLabel):
    def __init__(self,parent,type,shape,color,last_time):
        super().__init__(parent)
        self.side_width=min(parent.width(),parent.height()) // 2  #设置半径为父类宽高最小值的一半
        self.setGeometry(0,0,self.side_width,self.side_width)
        self.shape=shape
        self.last_time=last_time
        self.color=color
        if type==11:
            self.start_rect=QRectF(0,0,self.width(),self.height())
            self.end_rect=QRectF(self.parent().width()-self.side_width,self.parent().height()-self.side_width,self.side_width,self.side_width)
        elif type==12:
            self.start_rect=QRectF(parent.width()-self.side_width,parent.height()-self.side_width,self.side_width,self.side_width)
            self.end_rect=QRectF(0,0,self.width(),self.height())
        elif type==21:
            self.start_rect=QRectF((parent.width()-self.side_width)//2,0,self.side_width,self.side_width)
            self.end_rect=QRectF((parent.width()-self.side_width)//2,parent.height()-self.side_width,self.side_width,self.side_width)
        elif type==22:
            self.start_rect=QRectF((parent.width()-self.side_width)//2,parent.height()-self.side_width,self.side_width,self.side_width)
            self.end_rect=QRectF((parent.width()-self.side_width)//2,0,self.side_width,self.side_width)
        elif type==31:
            self.start_rect=QRectF(parent.width()-self.side_width,0,self.side_width,self.side_width)
            self.end_rect= QRectF(0,parent.height()-self.side_width,self.side_width,self.side_width)
        elif type==32:
            self.start_rect=QRectF(0,parent.height()-self.side_width,self.side_width,self.side_width)
            self.end_rect=QRectF(parent.width()-self.side_width,0,self.side_width,self.side_width)
        elif type==41:
            self.start_rect=QRectF(parent.width()-self.side_width,(parent.height()-self.side_width)//2,self.side_width,self.side_width)
            self.end_rect=QRectF(0,(parent.height()-self.side_width)//2,self.side_width,self.side_width)
        elif type==42:
            self.start_rect=QRectF(0,(parent.height()-self.side_width)//2,self.side_width,self.side_width)
            self.end_rect=QRectF(parent.width()-self.side_width,(parent.height()-self.side_width)//2,self.side_width,self.side_width)
        self.animation=QPropertyAnimation(self,b'geometry')
        self.animation.finished.connect(self.toggleAnimation)
        self.animationSpeed(dnspeed)
        self.startAnimation(dnopen,eval(dncurve))
    def paintEvent(self,event):
        super().paintEvent(event)
        painter=QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.shape==1:
            #计算圆的位置
            rect=self.rect().adjusted(1,1,-1,-1)
            #设置刷子
            brush=QBrush(QColor(self.color))  #设置刷子颜色
            painter.setBrush(brush)
            #绘制圆
            painter.drawEllipse(rect)
        elif self.shape==2:
            painter.fillRect(0,0,self.side_width,self.side_width,QColor(self.color))  #设置刷子颜色
        elif self.shape==3:
            #计算三角形的顶点坐标
            p1=QPointF(self.width()/2,(self.height()-self.side_width*0.866)/2)  #设置刷子颜色
            p2=QPointF((self.width()-self.side_width)/2,(self.height()+self.side_width*0.866)/2)
            p3=QPointF((self.width()+self.side_width)/2,(self.height()+self.side_width*0.866)/2)
            triangle=QPolygonF([p1,p2,p3])
            painter.setBrush(QBrush(QColor(self.color)))  #设置刷子颜色
            painter.drawPolygon(triangle)
    def toggleAnimation(self):
        #切换动画的起始值和结束值
        a,b=self.animation.startValue(),self.animation.endValue()
        a,b=b,a
        self.animation.setStartValue(a)
        self.animation.setEndValue(b)
        self.animation.start()
    def animationSpeed(self,speed):
        self.animation.setDuration(self.last_time*speed)
    def startAnimation(self,open,dynamic):
        self.animation.setStartValue(self.start_rect)
        self.animation.setEndValue(self.end_rect)
        if open==0:
            self.animation.setEasingCurve(dynamic) #设置缓动曲线
            self.animation.start()
        else:
            self.animation.stop()

class GetColor(QColorDialog):
    def __init__(self):
        super().__init__()  
    def getcolor(self):
        self.color=self.getColor()
        if self.color.isValid():
            return self.color.name()

class MainWindow(QMainWindow):
    answersignal=pyqtSignal(str)
    clearsignal=pyqtSignal(str)
    def __init__(self):
        super().__init__()
        self.code=None
        self.state=None
        self.thread=None
        self.question=None
        self.settingw=None
        self.historyw=None
        self.gemini=Gemini()
        self.setGeometry(450,50,m_width,m_height)
        self.initUI()
    def closeEvent(self,event):
        window=[self.settingw,self.historyw]
        for i in window:
            if i is not None:
                i.close()
        if self.thread is not None:
            if self.thread.is_alive():
                self.thread.join()
        event.accept()
    def initUI(self):
        self.setWindowIcon(QIcon('images/Gemini.ico'))
        center=QWidget(self)
        shapes=[
            {'type':21,'shape':1,'color':getcolor(),'last_time':6},
            {'type':22,'shape':1,'color':getcolor(),'last_time':5},
            {'type':31,'shape':2,'color':getcolor(),'last_time':7},
            {'type':41,'shape':3,'color':getcolor(),'last_time':8},
            {'type':12,'shape':3,'color':getcolor(),'last_time':9},
        ]
        label=BlurredLabel(self,shapes)
        self.setCentralWidget(center)
        self.setWindowTitle('Gemini AI')

        f1=QFrame(self)
        f1.resize(m_width,m_height)
        layout_f1=QVBoxLayout(f1)
        
        def settingwindow():
            self.settingw.show()
        def showhistory():
            self.historyw.show()
        layout_top=QHBoxLayout()
        layout_f1.addLayout(layout_top)
        b1=QPushButton()
        b1.clicked.connect(settingwindow)
        b1.setIcon(QIcon('images/setting.png'))
        b0=QPushButton()
        b0.clicked.connect(showhistory)
        for i in b0,b1:
            i.setStyleSheet('background:rgba(255,255,255,0)')
        b0.setIcon(QIcon('images/history.png'))
        layout_top.addWidget(b0)
        layout_top.addStretch(1)
        layout_top.addWidget(b1)

        l1=QLabel('Geimini AI')
        l1.setFont(QFont('微软雅黑',30))
        l1.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout_f1.addWidget(l1)
        layout_f1.addStretch()

        t1=QTextEdit()
        t1.setMinimumSize(int(m_width*0.9),int(m_height*0.3))
        layout_f1.addWidget(t1)
        layout_f1.addStretch(2)

        keywords=['网页','博客','文章','帖子','Wiki','文档','教程','手册','报告','百科','简历',
                      '电子书','演讲稿','课件','规范','合同','论文','文章','新闻','计划','指南','说明',
                      '分析','笔记','词典','诗歌','小说','剧本','攻略','日志','论文','新闻','公告']
        def answer():
            self.code=1
            for i in keywords:
                if i in self.question:
                    self.code=0
                    break
            answer=self.gemini.get_content(self.code,self.question)
            answer_text='Gemini:\n'+answer+'\n'
            if self.code==0:self.answersignal.emit('<br>'+answer_text)
            else:t2.append(answer_text)
            self.historyw.ta.append(answer_text)
            self.clearsignal.emit('signal')
            time.sleep(0.1)
            setenable(True)
        def sethtml(html):
            t2.insertHtml(html)
            clearcontent(t1)
            setenable(True)
        def answerthread():
            self.question=t1.toPlainText()
            if self.state==None:
                self.question+=',语言请用简体中文'
                self.state=1
            question_text='我:\n'+self.question
            self.historyw.ta.append(question_text)
            t2.append(question_text)
            self.thread=threading.Thread(target=answer)
            self.thread.start()
            t1.setText('请等待回答...')
            setenable(False)
        self.answersignal.connect(sethtml)
        self.clearsignal.connect(lambda:clearcontent(t1))
        layout_content=QHBoxLayout()
        b2=QPushButton('发送')
        b2.setStyleSheet('border-radius:15px')
        b2.setMinimumSize(int(m_width*0.5)-10,int(m_height*0.05))
        b2.clicked.connect(answerthread)
        def setenable(bool):
            b2.setEnabled(bool)
            b3.setEnabled(bool)
        def clearcontent(qt):
            qt.clear()
        b3=QPushButton('清空')
        b3.clicked.connect(lambda:clearcontent(t2))
        b3.setStyleSheet('border-radius:15px')
        b3.setMinimumSize(int(m_width*0.5)-10,int(m_height*0.05))
        for i in b2,b3:
            layout_content.addWidget(i)
        layout_f1.addLayout(layout_content)
        layout_f1.addStretch(1)

        t2=QTextEdit()
        t2.setReadOnly(True)
        t2.setMinimumSize(int(m_width*0.9),int(m_height*0.5))
    
        for i in t1,t2:
            i.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
            i.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        layout_f1.addWidget(t2)
        self.historyw=HistoryWindow()
        self.settingw=SettingWindow(center,label,t1,t2,b2,b3,self.historyw.center,self.historyw.label)

class HistoryWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.ta=None
        self.center=None
        self.label=None
        self.initUI()
    def initUI(self):
        self.setWindowTitle('对话历史')   
        self.setGeometry(50,100,400,400)
        self.setWindowIcon(QIcon('images/history.png'))
        self.center=QWidget(self)
        shapes=[
            {'type':11,'shape':1,'color':getcolor(),'last_time':6},
            {'type':21,'shape':3,'color':getcolor(),'last_time':5},
            {'type':31,'shape':1,'color':getcolor(),'last_time':7},
            {'type':41,'shape':2,'color':getcolor(),'last_time':8},
            {'type':12,'shape':1,'color':getcolor(),'last_time':9},
        ]
        self.label=BlurredLabel(self,shapes)
        self.setCentralWidget(self.center)

        f1=QFrame(self)
        layout_f1=QVBoxLayout(f1)
        f1.resize(400,400)
        self.ta=QTextEdit()
        self.ta.setMinimumSize(380,380)
        self.ta.setStyleSheet('background:rgba(255,255,255,0.5);border-radius:15px')
        self.ta.setReadOnly(True)
        layout_f1.addWidget(self.ta)

class SettingWindow(QMainWindow):
    def __init__(self,mwbg,mwlb,tq,ta,ba,bc,htbg,htlb):
        super().__init__()
        self.mwbg=mwbg
        self.mwlb=mwlb
        self.htbg=htbg
        self.htlb=htlb
        self.tq=tq
        self.ta=ta
        self.ba=ba
        self.bc=bc
        self.initUI()
    def initUI(self):
        self.setWindowTitle('设置')   
        self.setGeometry(m_width+450,100,400,470)
        self.setWindowIcon(QIcon('images/setting.png'))
        center=QWidget(self)
        shapes=[
            {'type':11,'shape':1,'color':getcolor(),'last_time':6},
            {'type':21,'shape':3,'color':getcolor(),'last_time':5},
            {'type':31,'shape':1,'color':getcolor(),'last_time':7},
            {'type':41,'shape':2,'color':getcolor(),'last_time':8},
            {'type':12,'shape':1,'color':getcolor(),'last_time':9},
        ]
        label=BlurredLabel(self,shapes)
        self.setCentralWidget(center)

        f1=QFrame(self)
        f1.resize(400,470)
        layout_f1=QVBoxLayout(f1)

        l1=QLabel('模糊设置')

        def blur_open(state,num):
            self.mwlb.blur(state,num)
            self.htlb.blur(state,num)
            label.blur(state,num)
            rwconfig.wconfig('blur','open',state)

        cb1=QCheckBox('取消模糊')
        if blopen==2:
            cb1.setChecked(True)
        else:cb1.setChecked(False)
        cb1.stateChanged.connect(lambda state: blur_open(state,blradius))

        def blur_radius(num):
            try:
                a=int(num)
                blur_open(0,a)
                cb1.setChecked(False)
                rwconfig.wconfig('blur','blur_radius',a)
            except ValueError:
                messagebox.show('模糊程度应为整型(int)')

        layout_blur=QHBoxLayout()
        l2=QLabel('模糊程度:')
        t1=QLineEdit()
        t1.setText(str(blradius))
        t1.setMaximumWidth(50)
        def showtext(text):
            QToolTip.showText(QCursor.pos(),text)
        b1=QPushButton()
        b1.setIcon(QIcon('images/warm.png'))
        b1.clicked.connect(lambda:showtext('数字越大性能开销越大!'))
        b2=QPushButton()
        b2.setIcon(QIcon('images/save.png'))
        b2.clicked.connect(lambda: blur_radius(t1.text()))
        qt=[l2,t1,b1,0,b2]
        for i in qt:
            if i==0:layout_blur.addStretch(1)
            else:layout_blur.addWidget(i)

        l3=QLabel('界面设置')
        layout_window=QVBoxLayout()

        layout_window1=QHBoxLayout()
        l4=QLabel('窗口背景色:')
        def setwindowcolor():
            color=GetColor().getcolor()
            if color is not None:
                self.mwbg.setStyleSheet('background:'+color)
                self.htbg.setStyleSheet('background:'+color)
                center.setStyleSheet('background:'+color)
                b3.setStyleSheet(center.styleSheet()+';border-radius:10px')
                rwconfig.wconfig('window','bg_color',color)

        b3=QPushButton()
        b3.setMaximumSize(40,40)
        b3.clicked.connect(setwindowcolor) 
        b13=QPushButton()
        b13.setIcon(QIcon('images/save.png'))
        qt=[l4,b3,0,b13]
        for i in qt:
            if i==0:layout_window1.addStretch(1)
            else:layout_window1.addWidget(i)

        layout_window2=QHBoxLayout()
        l5=QLabel('主题模式:')
        btg1=QButtonGroup()
        def settheme(color):
            if color=='default':
                self.mwbg.setStyleSheet('background:white')
                center.setStyleSheet('background:white')
                self.tq.setStyleSheet(f'background:rgba(255,255,255,0.5);border-radius:{qradius}px')
                self.ba.setStyleSheet('background:rgba(0,0,0,0.5);border-radius:15px')
            else:
                if color=='white':
                    self.mwbg.setStyleSheet('background:white')
                    center.setStyleSheet('background:white')
                    self.tq.setStyleSheet(f'background:rgba(0,0,0,0.5);border-radius:{qradius}px')
                    self.ba.setStyleSheet('background:rgba(0,0,0,0.5);border-radius:15px')
                else:
                    self.mwbg.setStyleSheet('background:black')
                    center.setStyleSheet('background:black')
                    self.tq.setStyleSheet(f'background:rgba(255,255,255,0.5);border-radius:{qradius}px')
                    self.ba.setStyleSheet('background:rgba(255,255,255,0.5);border-radius:15px')
            self.ta.setStyleSheet(self.tq.styleSheet())
            self.bc.setStyleSheet(self.ba.styleSheet())
            b3.setStyleSheet(center.styleSheet()+';border-radius:10px')
            rwconfig.wconfig('window','theme',color)
        b4=QRadioButton('明亮')
        b4.clicked.connect(lambda:settheme('white'))
        b5=QRadioButton('暗黑')
        b5.clicked.connect(lambda:settheme('black'))
        b6=QRadioButton('默认')
        b6.clicked.connect(lambda:settheme('default'))
        for i in l5,b6,b4,b5:
            if i!=l5:btg1.addButton(i)
            layout_window2.addWidget(i)
        if bgtheme=='default':b6.click()
        elif bgtheme=='white':b4.click()
        else:b5.click()

        def setradius(code,te,num):
            try:
                a=int(num)
                style=te.styleSheet()
                patten=re.findall(find_radius,style)[0]
                style=str(style).replace(patten,num)
                te.setStyleSheet(style)
                rwconfig.wconfig('window',code,a)
            except ValueError:
                messagebox.show('圆角应为整形(int)')
        layout_window3=QHBoxLayout()
        l6=QLabel('输入框圆角:')
        t2=QLineEdit()
        t2.setMaximumWidth(50)
        t2.setText(str(qradius))
        b7=QPushButton()
        b7.setIcon(QIcon('images/save.png'))
        b7.clicked.connect(lambda:setradius('q_radius',self.tq,t2.text()))
        qt=[l6,t2,0,b7]
        for i in qt:
            if i==0:layout_window3.addStretch(1)
            else:layout_window3.addWidget(i)

        layout_window4=QHBoxLayout()
        l7=QLabel('回答框圆角:')
        t3=QLineEdit()
        t3.setMaximumWidth(50)
        t3.setText(str(aradius))
        b8=QPushButton()
        b8.setIcon(QIcon('images/save.png'))
        b8.clicked.connect(lambda:setradius('a_radius',self.ta,t3.text()))
        qt=[l7,t3,0,b8]
        for i in qt:
            if i==0:layout_window4.addStretch(1)
            else:layout_window4.addWidget(i)

        for i in layout_window1,layout_window2,layout_window3,layout_window4:
            layout_window.addLayout(i)

        l8=QLabel('动效设置')
        layout_dynamic=QHBoxLayout()
        def setdynamic(state,curve):
            if state==2:
                for i in ml:
                    i.startAnimation(state,None)
            else:
                for i in ml:
                    i.startAnimation(state,curve)
                    rwconfig.wconfig('dynamic','curve','QEasingCurve.'+str(curve_dict[combobox1.currentText()]))
            rwconfig.wconfig('dynamic','open',state)
        cb2=QCheckBox('关闭动效')
        if dnopen==2:
            cb2.setChecked(True)
        else:cb2.setChecked(False)
        cb2.stateChanged.connect(lambda state:setdynamic(state,eval(dncurve)))
        l9=QLabel('运动速度:')
        t4=QLineEdit()
        t4.setMaximumWidth(50)
        t4.setText(str(dnspeed))
        def setspeed(num):
            try:
                a=int(num)
                for i in ml:
                    i.animationSpeed(a)
                rwconfig.wconfig('dynamic','speed',a)
            except ValueError:
                messagebox.show('运动速度应为整形(int)')
        b9=QPushButton()
        b9.setIcon(QIcon('images/warm.png'))
        b9.clicked.connect(lambda:showtext('数字越大运动越慢,建议500-1000'))
        b10=QPushButton()
        b10.setIcon(QIcon('images/save.png'))
        b10.clicked.connect(lambda:setspeed(t4.text()))

        for i in t1,t2,t3,t4:
            i.setStyleSheet('background:rgba(255,255,255,0.5);border-radius:6px')

        qt=[l9,t4,b9,0,b10]
        for i in qt:
            if i==0:layout_dynamic.addStretch(1)
            else:layout_dynamic.addWidget(i)

        layout_dynamic1=QHBoxLayout()
        curve_dict={
            "线性": QEasingCurve.Type.Linear,
            "二次方进入": QEasingCurve.Type.InQuad,
            "二次方退出": QEasingCurve.Type.OutQuad,
            "二次方进入退出": QEasingCurve.Type.InOutQuad,
            "三次方进入": QEasingCurve.Type.InCubic,
            "三次方退出": QEasingCurve.Type.OutCubic,
            "三次方进入退出": QEasingCurve.Type.InOutCubic,
            "四次方进入": QEasingCurve.Type.InQuart,
            "四次方退出": QEasingCurve.Type.OutQuart,
            "四次方进入退出": QEasingCurve.Type.InOutQuart
        }
        curve_des=[
            "线性曲线，即匀速运动",
            "二次方曲线，开始缓慢，后期加速",
            "二次方曲线，开始加速，后期减速",
            "二次方曲线，开始缓慢，后期加速，再后期减速",
            "三次方曲线，开始缓慢，后期加速",
            "三次方曲线，开始加速，后期减速",
            "三次方曲线，开始缓慢，后期加速，再后期减速",
            "四次方曲线，开始缓慢，后期加速",
            "四次方曲线，开始加速，后期减速",
            "四次方曲线，开始缓慢，后期加速，再后期减速"
        ]
        
        l10=QLabel('动画曲线:')
        combobox1=QComboBox()

        for key,value in curve_dict.items():
            combobox1.addItem(key)
            if str(value)==dncurve[13:]:
                combobox1.setCurrentText(key)

        b11=QPushButton()
        b11.setIcon(QIcon('images/tip.png'))
        b11.clicked.connect(lambda:showtext(curve_des[combobox1.currentIndex()]))
        b12=QPushButton()
        b12.setIcon(QIcon('images/save.png'))
        b12.clicked.connect(lambda:setdynamic(0,curve_dict[combobox1.currentText()]))

        layout_update=QVBoxLayout()
        l11=QLabel('更新设置')
        def setinterval(days):
            rwconfig.wconfig('update','interval',days)
        layout_update1=QHBoxLayout()
        interval_dict={'每次':0,'1天':1,'3天':3,'5天':5,'7天':7}
        l12=QLabel('检查间隔:')
        combobox2=QComboBox()
        for key,value in interval_dict.items():
            combobox2.addItem(key)
            if value==interval:combobox2.setCurrentText(key)
        b14=QPushButton()
        b14.setIcon(QIcon('images/save.png'))
        b14.clicked.connect(lambda:setinterval(interval_dict[combobox2.currentText()]))
        for i in l12,combobox2,0,b14:
            if i==0:layout_update1.addStretch()
            else:layout_update1.addWidget(i)

        l13=QLabel('当前版本:'+str(VERSION))
        global qt_newversion
        newversion=checkupdate.get_data()
        if newversion is None:result='检查失败!'
        else:result=str(newversion['version'])
        l14=QLabel('云端版本:'+result)
        qt_newversion=l14
        global qt_lasttime
        l15=QLabel('检查时间:'+str(lasttime))
        qt_lasttime=l15
        layout_update2=QHBoxLayout()
        for i in l13,l14,l15:
            if i==0:layout_update2.addStretch()
            else:layout_update2.addWidget(i)
        b18=QPushButton('检查更新')
        b18.clicked.connect(lambda:update_thread(True))
        layout_update3=QVBoxLayout()
        layout_update3.addWidget(b18)
        for i in layout_update1,layout_update2,layout_update3:
            layout_update.addLayout(i)

        for i in l1,l3,l8,l11:
            i.setFont(QFont('微软雅黑',15))
            i.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i in combobox1,combobox2:
            i.setStyleSheet("QComboBox { background-color: rgba(255,255,255,0.1); }"
                        "QComboBox QAbstractItemView { background-color: rgba(255,255,255,0.1); }")
            
        for i in b1,b2,b7,b8,b9,b10,b11,b12,b13,b14:
            i.setStyleSheet('background:rgba(0,0,0,0)')

        qt=[l10,combobox1,b11,0,b12]
        for i in qt:
            if i==0:layout_dynamic1.addStretch(1)
            else:layout_dynamic1.addWidget(i)

        for i in [l1,cb1,layout_blur,l3,layout_window,l8,cb2,layout_dynamic,layout_dynamic1,l11,layout_update]:
            if i in [layout_blur,layout_window,layout_dynamic,layout_dynamic1,layout_update]:layout_f1.addLayout(i)
            else:layout_f1.addWidget(i)
        layout_f1.addStretch(1)

        self.mwbg.setStyleSheet('background:'+bgcolor)
        center.setStyleSheet('background:'+bgcolor)
        b3.setStyleSheet(center.styleSheet()+';border-radius:10px')
    
def update_thread(skip=False):
    update=threading.Thread(target=checkupdate.check,args=(skip,))
    update.start()

def main():
    app=QApplication(sys.argv)
    global m_width,m_height
    m_width=int(app.primaryScreen().size().width()*0.4)
    m_height=int(app.primaryScreen().size().height()*0.88)
    mainWindow=MainWindow()
    mainWindow.show()
    update_thread()
    sys.exit(app.exec())

if __name__=='__main__':
    main()