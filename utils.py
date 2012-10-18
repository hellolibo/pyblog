#!C:\Python26\python.exe -u
#coding:utf-8
import web
import re
import config

def isnumber(s): 
    try: 
        float(s) 
        return True 
    except ValueError: 
        return False 

#分页
def pages(pagecount=0,curpage=1,showsize=10,url=''):
    pagecount,curpage,showsize=int(pagecount),int(curpage),int(showsize)
    if url:
        url="&"+url
    if pagecount<=0:
        pagecount=1
    if showsize<=0:
        showsize=1
    if curpage>pagecount:
        curpage=pagecount
    elif curpage<1:
        curpage=1
        
    if curpage==1:
        previous=''
    elif curpage>1:
        previous=u'<a href="?curpage=%s%s" class="p_pre">上一页</a>'%(curpage-1,url)
    if curpage==pagecount:
        next=''
    elif curpage<pagecount:
        next=u'<a href="?curpage=%s%s" class="p_next">下一页</a>'%(curpage+1,url)
    
    movestep=showsize/2
    if curpage<movestep:
        start=1
        end=pagecount
    else:
        end=curpage+movestep
        start=curpage-movestep
        if end>pagecount:end=pagecount
        if start<1:start=1
    pages_link=''
    if start==end:
        return ""
    else:
        for num in range(start,end+1):
            if num==curpage:
                pages_link+='<strong>%s</strong>'%num
            else:
                pages_link+='<a href="?curpage=%s%s">%s</a>'%(num,url,num)
        
        return '<div class="pages">%s%s%s</div>'%(previous,pages_link,next)
    
def clearHtml(str=''):
    str=re.sub(r'<[^>]+\/?>','',str)
