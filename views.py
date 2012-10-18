#!C:\Python26\python.exe -u
#coding:utf-8
import web
import re
import string
import os
import datetime
from datetime import datetime
import hashlib 
import config
import utils as util
from model import *

def initlog(logFilePath):
    import logging
    logger = logging.getLogger()
    hdlr = logging.FileHandler(logFilePath)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
    hdlr.setFormatter(formatter)
    logger.addHandler(hdlr)
    logger.setLevel(logging.NOTSET)
    return logger

logger = initlog(config.LOG_PATH)

#缓存常用数据
def GetCategory(cates):
    for n in cates:
        yield n
        if len(n.children)>0:
            for m in GetCategory(n.children): #递归调用生成器时，一定要用迭代调用
                yield m
def _category():
    return [i for i in GetCategory(session.query(Categories).filter_by(parent_id=None).all())]
def _newcomment(num=10):
    return session.query(Comment).order_by(Comment.addTime.asc()).all()[:num]
def _tags():
    tag=[]
    fontsizeMax=30
    fontsizeMin=10

    tag_count_subquery = session.query(Article_Tag.tag_id, func.count('*').label('tagcount')).group_by(Article_Tag.tag_id).subquery()
    tags = session.query(Tag, tag_count_subquery.c.tagcount).join((tag_count_subquery, Tag.id==tag_count_subquery.c.tag_id)).order_by(tag_count_subquery.c.tagcount.desc()).all()
    
    if not tags:
        return tag
    tags_len=len(tags)
    div=(fontsizeMax-fontsizeMin)/tags_len
    divs=[d+div for d in range(fontsizeMin,fontsizeMax-1)]
    count_temp=0
    i=0
    for t,c in tags:
        if count_temp!=c:
            i+=1
        tag.append({
            'tag':t.tag,
            'tagcount':c,
            'size':int(divs[i])
        })
        count_temp=c
    return tag
def _links():
    return session.query(Links).all()
def _archive(num=12):
    return session.query(Archive).order_by(Archive.addTime.desc()).limit(num).all()

class user:
    instance_user=None
    def __new__(self,*args, **kwargs):
        if not self.instance_user:
            self.instance_user = super(user,self).__new__(self,*args, **kwargs)
        return self.instance_user
    
    def __init__(self):
            self._se=web.config.get('_session')
            logger.info(self._se.logged)
    
    def check_user(self,name,pwd):
        if name=="" or pwd=="":
            return {"success":False,"error":1}
        user=session.query(User).filter_by(accountname=name).filter_by(password=hashlib.new("md5",pwd).hexdigest()).first()
        if user is None:
            return {"success":False,"error":2}
        else:
            logger.info(user)
            self._se.logged = True
            self._se.accountname = user.accountname
            self._se.dispname = user.dispname
            self._se.id = user.id
            self._se.isadmin = user.isadmin
            return {"success":True}
            
    def get_current_user(self):
            return self._se
    def clear(self):
        self._se.logged = False
        self._se.accountname = ''
        self._se.dispname = ''
        self._se.id = 0
        self._se.isadmin = False
        
class base_view:
    def __init__(self):
        u = user()
        self.login_user = u.get_current_user()
    
class base_manage_view(base_view):
    def __init__(self,isadmin=''):
        base_view.__init__(self)
        web.header('Content-type','text/html;UTF-8')
        if not self.login_user.logged: #是否登录
            web.seeother("/login/")
        elif isadmin=='admin' and not self.login_user.isadmin: #是否必须是管理员
            web.redirect('/error/403')
            
class base_blog_view(base_view):
    def __init__(self):
        base_view.__init__(self)
        web.header('Content-type','text/html;UTF-8')

#主页面
class default(base_blog_view):
    def GET(self):
        query=web.input(p=0,curpage=1)
        try:
            curpage=int(query.curpage) #当前页
            p=int(query.p)
        except:
            return web.notfound('not found the page')
            
        if p==0:        
            articles_se=session.query(Article).filter_by(published=True).order_by(Article.addTime.desc())
            articles_count=articles_se.count()

            offset=(curpage-1)*config.HOME_PAGE_LEN
            p=divmod(articles_count,config.HOME_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
            articles=articles_se.limit(config.HOME_PAGE_LEN).offset(offset).all()
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage'))
            return render_blog.default(locals(),self)
        else:
            article=session.query(Article).filter_by(id=p).first()
            comments=article.comments

            offset=(curpage-1)*config.COMMENT_PAGE_LEN
            p=divmod(len(comments),config.COMMENT_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
                
            comments=comments[offset:offset+config.COMMENT_PAGE_LEN-1]
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
            cookie={
                'author': web.cookies(author="").author,
                'email':web.cookies(email="").email,
                'weburl':web.cookies(weburl="").weburl
            }
            if article.template :
                return (web.template.frender('templates/%s'%article.template))(locals(),self)
            else:
                return render_blog.article_detail(locals(),self)
            
class article_by_slug(base_blog_view):
    
    def GET(self,slug):
        query=web.input(curpage=1)
        curpage = query.curpage
        if slug:
            article=session.query(Article).filter(Article.slug==slug).first()
            comments=article.comments
            offset=(curpage-1)*config.COMMENT_PAGE_LEN
            p=divmod(len(comments),config.COMMENT_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
            comments=comments[offset:offset+config.COMMENT_PAGE_LEN-1]
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
            cookie={
                'author': web.cookies(author="").author,
                'email':web.cookies(email="").email,
                'weburl':web.cookies(weburl="").weburl
            }
            return render_blog.article_detail(locals(),self)
        else:
            return web.notfound('not found the page')
            
class article_by_tag(base_blog_view):
    def GET(self,f_tag):
        query=web.input(curpage=1)
        curpage = query.curpage
         
        list_title = u"%s的标签文档"%(f_tag)
        list_description = list_title
        list_keywords = list_title
        articles = session.query(Article).filter(Article.tags.any(Tag.tag == f_tag)).order_by(Article.addTime.desc())
        
        offset=(curpage-1)*config.COMMENT_PAGE_LEN
        p=divmod(articles.count(),config.COMMENT_PAGE_LEN)
        if p[1]>0:
            pagecount=p[0]+1
        else:
            pagecount=1
        articles=articles.limit(config.COMMENT_PAGE_LEN).offset(offset).all()
        pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
        cookie={
            'author': web.cookies(author="").author,
            'email':web.cookies(email="").email,
            'weburl':web.cookies(weburl="").weburl
        }
        return render_blog.article_list(locals(),self)
            
class article_by_month(base_blog_view):
        def GET(self,f_year,f_month):
            query=web.input(curpage=1)
            curpage = query.curpage
             
            list_title = u"%s年%s月文档"%(f_year,f_month)
            list_description = list_title
            list_keywords = list_title
            articles = session.query(Article).filter("date_format(addTime,'%Y-%m') = '"+f_year+"-"+f_month+"'").order_by(Article.addTime.desc())
            
            offset=(curpage-1)*config.COMMENT_PAGE_LEN
            p=divmod(articles.count(),config.COMMENT_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
            articles=articles.limit(config.COMMENT_PAGE_LEN).offset(offset).all()
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
            cookie={
                'author': web.cookies(author="").author,
                'email':web.cookies(email="").email,
                'weburl':web.cookies(weburl="").weburl
            }
            return render_blog.article_list(locals(),self)
            
class article_by_year(base_blog_view):
        def GET(self,f_year):
            query=web.input(curpage=1)
            curpage = query.curpage
             
            list_title = u"%s年"%(f_year)
            list_description = list_title
            list_keywords = list_title
            articles = session.query(Article).filter("date_format(addTime,'%Y') = '"+f_year+"'").order_by(Article.addTime.desc())
            
            offset=(curpage-1)*config.COMMENT_PAGE_LEN
            p=divmod(articles.count(),config.COMMENT_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
            articles=articles.limit(config.COMMENT_PAGE_LEN).offset(offset).all()
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
            cookie={
                'author': web.cookies(author="").author,
                'email':web.cookies(email="").email,
                'weburl':web.cookies(weburl="").weburl
            }
            return render_blog.article_list(locals(),self)
 
class article_by_category(base_blog_view):
        def GET(self,f_cate_slug):
            query=web.input(curpage=1)
            curpage = query.curpage
            
            category = session.query(Categories).filter(Categories.slug == f_cate_slug).first()
            if category:
                list_title = u"分类:%s"%(category.title)
                list_description = list_title
                list_keywords = list_title
            else:
                list_title = u"分类:无此分类"
                list_description = list_title
                list_keywords = list_title
                
            articles = session.query(Article).filter(Article.categories.any(Categories.slug == f_cate_slug)).order_by(Article.addTime.desc())
            
            offset=(curpage-1)*config.COMMENT_PAGE_LEN
            p=divmod(articles.count(),config.COMMENT_PAGE_LEN)
            if p[1]>0:
                pagecount=p[0]+1
            else:
                pagecount=1
            articles=articles.limit(config.COMMENT_PAGE_LEN).offset(offset).all()
            pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage')+'#comment')
            cookie={
                'author': web.cookies(author="").author,
                'email':web.cookies(email="").email,
                'weburl':web.cookies(weburl="").weburl
            }
            return render_blog.article_list(locals(),self)
            
class post_comment(base_blog_view):
    def POST(self):
        referer = web.ctx.env.get('HTTP_REFERER', pyblog.urlpath)
        query=web.input(f_article_id='',f_author='',f_email='',f_weburl='',f_content='')
        if query.f_article_id=="" or query.f_author=='' or query.f_email=='' or query.f_content=='':
            return render.error({'error':['缺少关键数据']},self)
        comment=Comment()
        article=session.query(Article).filter_by(id=query.f_article_id).first()
        if article is None:
            return render.error({'error':['要留言的文章不存在']},self)
        else:
            comment.article_id=article.id
            article.comment_count +=1 
        if re.search(r'^http://',query.f_weburl) is None:
            f_weburl=r'http://%s'%query.f_weburl
        else:
            f_weburl=query.f_weburl
            
        comment.author=query.f_author
        comment.email=query.f_email
        comment.content=query.f_content
        comment.weburl=f_weburl
        comment.ip=web.ctx.ip
        session.add(comment)
        session.commit()
        
        web.setcookie('author',query.f_author, 3600*24*30)
        web.setcookie('email',query.f_email, 3600*24*30)
        web.setcookie('weburl',f_weburl, 3600*24*30)
        return web.seeother(referer)

#后台管理
class manage_users(base_manage_view):
    def __init__(self):
        base_manage_view.__init__(self,'admin')
        
    def GET(self):
        users=session.query(User).all()
        user_count=session.query(User).count()
        return render_manage.manage_users(locals(),self)
        
class manage_users_del(base_manage_view):
    def __init__(self):
        base_manage_view.__init__(self,'admin')
        
    def GET(self):
        query=web.input(id='')
        if query.id!="":
            del_users = session.query(User).filter_by(id!=self.login_user.id).filter_by(id.in_([int(i) for i in string.split(query.id,',')])).all()
            if del_users:
                for u in del_users:
                    session.delete(u)
                session.commit()

        web.seeother('/manage/users')
        
class manage_users_edit(base_manage_view):
    def __init__(self):
        base_manage_view.__init__(self,'admin')
    
    def GET(self):
        formdata={
            'accountname':'',
            'dispname':'',
            'password':'',
            'email':'',
            'id':''
        }
        query=web.input(id='')
        error=[]
        
        if len(query.id)>0:#编辑
            user=session.query(User).filter_by(id=query.id).first()
            if user:
                formdata['accountname'] = user.accountname
                formdata['dispname']=user.dispname
                formdata['email']=user.email
                formdata['id']=query.id
            else:
                return web.notfound()
        return render_manage.manage_users_edit(locals(),self)
    def POST(self):
        query=web.input(f_dispname='',f_accountname='', f_email='',f_id='',f_password='')
        error=[]
        password_md5 = hashlib.md5(query.f_password).hexdigest()

        if query.f_accountname == '' or query.f_email == '' or query.f_password == '':
            error.append('关键数据没有')
        else:
            if len(query.f_id)==0:
                user = User()
                user.isadmin=False
            else:
                user=session.query(User).filter_by(id=query.f_id).first()
                if not user:
                    error.append('没有此用户')
                elif user.password != password_md5 :
                    error.append('密码不正确')
            
            if not re.search('^.*@.*$',query.f_email) :
                error.append('email格式不正确')
            
            if user :
                user.accountname = query.f_accountname
                user.dispname=query.f_dispname
                user.password = password_md5
                user.email=query.f_email
                session.add(user)
                session.commit()
                
        if len(error)==0:
            return web.seeother('/manage/users')
        else:
            return render_manage.manage_users_edit(locals(),self)
        
class manage_config(base_manage_view):
    def __init__(self):
        base_manage_view.__init__(self,'admin')

    def GET(self):
        formdata={
            'blogtitle':pyblog.blogtitle,
            'subtitle':pyblog.subtitle,
            'description':pyblog.description,
            'urlpath':pyblog.urlpath,
        }
        error=[]
        return render_manage.manage_config(locals(),self)
    
    def POST(self):
        query=web.input(f_subtitle='',f_blogtitle='',f_description='')
        error=[]
        f_blogtitle=query.f_blogtitle.strip()
        f_subtitle=query.f_subtitle.strip()
        f_description=query.f_description.strip()
        f_urlpath=query.f_urlpath.strip()
        
        if error:
            return render_manage.manage_config(locals(),self)
        else:
            pyblog.blogtitle=f_blogtitle
            pyblog.subtitle=f_subtitle
            pyblog.description=f_description
            pyblog.urlpath=f_urlpath
            
            session.commit()
            
            web.seeother('/manage/config')
            
class manage_article(base_manage_view):
    def GET(self):
        query=web.input(curpage=1)
        curpage=int(query.curpage) #当前页
        
        articles_se=session.query(Article).order_by(Article.addTime.desc())
        articles_count=articles_se.count()
        
        offset=(curpage-1)*config.DEFAULT_PAGE_LEN
        p=divmod(articles_count,config.DEFAULT_PAGE_LEN)
        if p[1]>0:
            pagecount=p[0]+1
        else:
            pagecount=1
        articles=articles_se.limit(config.DEFAULT_PAGE_LEN).offset(offset).all()
        
        pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage'))
        category=_category()
        return render_manage.manage_article(locals(),self)
    
class manage_article_edit(base_manage_view):
    def GET(self):
        query=web.input(id='')
        error=[]
       
        category=[i for i in GetCategory(session.query(Categories).filter_by(parent_id=None).all())]
        formdata={
                'cateids':[],
                'id':'',
                'title':'',
                'content':'',
                'template':'',
                'summary':'',
                'tags':'',
                'slug':'',
                'published':True,
                'istop':False,
                'iscomment':True
            }
        if len(query.id)!=0: #修改
            article=session.query(Article).filter_by(id=query.id).first()
            if article:
                formdata['cateids']=article.cateids
                formdata['id']=article.id
                formdata['title']=article.title
                formdata['content']=article.content
                formdata['template']=article.template
                formdata['summary']=article.summary
                formdata['tags']=article.tagsStr
                formdata['slug']=article.slug
                formdata['published']=article.published
                formdata['istop']=article.isTop
                formdata['iscomment']=article.isComment
            else:
                return web.notfound()
                
        return render_manage.manage_article_edit(locals(),self)
        
    def POST(self):
        query=web.input(f_id='',f_published=0,f_istop=0,f_iscomment=0,f_cateid=[],f_content='') #注意select没有值时，input里不会出现他的项

        error=[]
        isEdit = len(query.f_id)!=0
        
        if isEdit:  #修改
            try:
                article=session.query(Article).filter_by(id=query.f_id).first()
            except:
                error.append('没有这篇文章')
                
                return render_manage.manage_article_edit(locals(),self)
            article.modTime=datetime.datetime.now()
        else:
            article=Article()
        
        if len(query.f_title)==0:
            error.append('没有文章标题')
        else:
            article.title=query.f_title
            
        if len(query.f_slug)>0 and not re.match(r'^[\-_\w\d]+$',query.f_slug):
            error.append('slug格式不正确，或已存在')
        
        article.slug=re.sub(r"[\s]+",'_',query.f_slug)
        article.content=query.f_content.replace("/r","")
        article.template=query.f_template
        article.summary=query.f_summary
        article.published=bool(query.f_published)
        article.isTop=bool(query.f_istop)
        article.isComment=bool(query.f_iscomment)
        article.author_id=self.login_user.id
        article.author_name=self.login_user.dispname
        
        if len(error)>0:
            return render_manage.manage_article_edit(locals(),self)
        else:
            session.add(article)
            
            tags = string.split(query.f_tags,",")
            for t in tags:
                article.tags.append(Tag.create(t))
            
            for cid in query.f_cateid:
                article.categories.append(session.query(Categories).filter_by(id = cid).first())
            
            session.commit()

            if not isEdit:  #新添加
                article.update_archive(1)
            web.seeother('/manage/article')

class manage_article_del:
    def GET(self):
        query=web.input(id='')
        if query.id!="":
            del_arts=session.query(Article).filter(Article.id.in_([int(i) for i in string.split(query.id,',')])).all()
            if del_arts:
                for art in del_arts:
                    art.update_archive(-1)
                    session.delete(art)
                session.commit()
        web.seeother('/manage/article')
    
class manage_category(base_manage_view):
    def GET(self):
        category=_category()
        
        return render_manage.manage_category(locals(),self)
        
class manage_category_edit(base_manage_view):
    def GET(self):
        query=web.input(id='')
        error=[]

        category=session.query(Categories).all()
        formdata={
                'id':'',
                'title':'',
                'description':'',
                'keyword':'',
                'slug':'',
                'order':0,
                'parent_id':''
            }
        if len(query.id)!=0: #修改
            thecate=session.query(Categories).filter_by(id=query.id).first()
            category=session.query(Categories).filter(Categories.id!=query.id).all()
            
            if thecate is None:
                return web.notfound()
            else:
                formdata['id']=thecate.id
                formdata['title']=thecate.title
                formdata['description']=thecate.description
                formdata['keyword']=thecate.keyword
                formdata['slug']=thecate.slug
                formdata['order']=thecate.order
                formdata['parent_id']=thecate.parent_id or ''
        return render_manage.manage_category_edit(locals(),self)
        
    def POST(self):
        query=web.input(f_id='',f_order=0,f_parent='',f_title='')
        error=[]
        f_id=query.f_id
        
        if f_id!='':  #修改
            cate=session.query(Categories).filter_by(id=f_id).first()
            
            if not cate:
                error.append(u'无效的分类')
                return render_manage.manage_category_edit(locals(),self)
        else:  #添加
            cate=Categories()
        
        if len(query.f_title)==0:
            error.append(u'没有分类名称')
        else:
            cate.title=query.f_title
            
        cate.description=query.f_description
        cate.keyword=query.f_keyword
        
        try:
            cate.order=int(query.f_order)
        except:
            cate.order=0
        
        cate.parent_id=query.f_parent!='' and query.f_parent or None
    
        if len(query.f_slug)>0 and re.match(r'^[\-_\w\d]+$',query.f_slug) is not None:
            cate.slug=query.f_slug
        else:
            error.append(u'slug格式不正确，或已存在')
            
        if len(error)>0:
            return render_manage.manage_category_edit(locals(),self)
        else:
            session.add(cate)
            session.commit()
            web.seeother('/manage/category')
            
class manage_category_del(base_manage_view):
    def GET(self):
        query=web.input(id='')
        if query.id!="":
            del_cats=session.query(Categories).filter(Categories.id.in_([int(_id) for _id in string.split(query.id,',')])).all()
            if del_cats:
                for q in del_cats:
                    for son in q.children:
                        son.parent_id=None
                    session.delete(q)
                session.commit()
        web.seeother('/manage/category')
        
class manage_links(base_manage_view):
    def GET(self):
        links=session.query(Links).all()
        links_count=len(links)
        return render_manage.manage_links(locals(),self)
                
class manage_links_edit(base_manage_view):
    def GET(self):
        query=web.input(id='')
        error=[]
        formdata={
            'title':'',
            'href':'',
            'remark':'',
            'id':''
        }
        if len(query.id)>0:
            link=session.query(Links).get(int(query.id))
            formdata['title']=link.title
            formdata['href']=link.href
            formdata['remark']=link.remark
            formdata['id']=query.id
        return render_manage.manage_links_edit(locals(),self)
        
    def POST(self):
        error=[]
        query=web.input(f_id='',f_title='',f_href='',f_remark='')
        if query.f_title=='' or query.f_href=='':
            error.append("缺少必要参数")
            return render_manage.manage_links_edit(locals(),self)
        elif query.f_id=='': 
            link=Links()
        else:
            link=session.query(Links).get(int(query.f_id))
            
        link.title=query.f_title
        link.href=query.f_href
        link.remark=query.f_remark
        session.add(link)
        session.commit()
        return web.Redirect('/manage/links')
        
class manage_links_del(base_manage_view):
    def GET(self):
        query=web.input(id='')
        if len(query.id)>0:
            del_links=session.query(Links).filter(Links.id.in_([int(_id) for _id in string.split(query.id,',')])).all()
            if del_links:
                for link in del_links:
                    session.delete(link)
                session.commit()
        web.seeother('/manage/links')
        
class manage_comments(base_manage_view):
    def GET(self):
        comments = session.query(Comment).all()
        comments_count =  len(comments)
        return render_manage.manage_comments(locals(),self)   
 
class manage_comments_del(base_manage_view):
    def GET(self):
        query = web.input(id='')
        if len(query.id)>0:
            del_comment=session.query(Comment).filter(Comment.id.in_([int(i) for i in string.split(query.id,',')])).all()
            if del_comment:
                for comm in del_comment:
                    session.delete(comm)
                session.commit()
        web.seeother('/manage/comments')
 
class manage_media(base_manage_view):
    def GET(self):
        query=web.input(curpage=1)
        curpage=int(query.curpage) #当前页
        
        medias_se=session.query(Media).order_by(Media.addTime.desc())
        medias_count=medias_se.count()
        
        offset=(curpage-1)*config.DEFAULT_PAGE_LEN
        p=divmod(medias_count,config.DEFAULT_PAGE_LEN)
        if p[1]>0:
            pagecount=p[0]+1
        else:
            pagecount=1
        medias=medias_se.limit(config.DEFAULT_PAGE_LEN).offset(offset).all()
        pages=util.pages(pagecount,curpage,10,'&'.join('%s=%s'%(a,b) for a,b in query.items() if a!='curpage'))
        return render_manage.manage_media(locals(),self)
        
class manage_media_del(base_manage_view):
    def GET(self):
        query=web.input(id='')
        if query.id!='':
            del_meds=session.query(Media).filter(Media.id.in_([int(_id) for _id in string.split(query.id,',')])).all()
            if del_meds:
                for m in del_meds:
                    session.delete(m)
            session.commit()
        web.Redirect("/manage/media")
            
class manage_upload(base_manage_view):
    def POST(self):
        query=web.input(f_file={},f_mode='')
        
        if "f_file" in query:
            filename = query.f_file.filename
            mtype =os.path.splitext(filename)[1][1:]
            bits = query.f_file.value
            floder = config.UPLOAD_PATH+"/"+(datetime.datetime.now()).strftime('%Y-%m')
            cur_dir = os.path.abspath(os.curdir)
            savePath = (cur_dir+floder).replace("/","\\")
            if not os.path.isdir(savePath): 
                os.makedirs(savePath)
            
            fout = open(savePath +'\\'+ filename,'wb')
            fout.write(query.f_file.file.read())
            fout.close()
            
            media=Media(name = filename, mtype = mtype, url=floder+"/"+filename, size = len(bits))
            session.add(media)
            session.commit()
        
        else:
            web.Redirect("/manage/media")
        if query.f_mode.lower()=='ajax':
            return r'''
                <!DOCTYPE HTML>
                <html lang="en-US">
                <head>
                    <meta charset="UTF-8">
                    <title>back</title>
                </head>
                <body>
                    <script>parent.insertImg('<img src="%s/%s" />');</script>
                </body>
                </html>
            '''%(floder,filename)
        else:
            raise web.seeother('/manage/media')

class login(base_blog_view):
    def GET(self):
        error=[]
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        return render.login(locals(),self)
        
    def POST(self):
        u = user()
        error=[]
        query=web.input(f_uname='',f_pwd='',f_referer='')
        referer = query.f_referer
        if query.f_uname=='' or query.f_pwd=='':
            error.append('帐号密码不能为空')
        else:
            u_check = u.check_user(query.f_uname,query.f_pwd)
            if not u_check['success']:
                error.append('帐号密码有误')
            
        if len(error)>0:
            return render.login(locals(),self)
        else:
            cur_u = u.get_current_user()

            if cur_u:
                if cur_u.isadmin:
                    web.seeother('/manage/config')
                else:
                    web.seeother(query.f_referer or '/manage/article')
                    
            else:
                return u_check
            
class logout:
    def GET(self):
        u = user()
        u.clear()
        referer = web.ctx.env.get('HTTP_REFERER', '/')
        web.seeother(referer)
#-----------前台部分-----------------------------
class get_media:
    def GET(self,slug):
        media=Media.get(slug)
        if media:
            web.ok(
                {
                    'Expires':'Thu, 15 Apr 3010 20:00:00 GMT',
                    'Cache-Control':'max-age=3600,public',
                    'Content-Type':str(media.mtype)
                }
            )
            a=web.input(a='')['a']
            if a and a.lower()=='download':
                media.download+=1
                media.put()
            return media.bits
        else:
            return web.notfound()
#------------------------------------------------        
class error(base_view):
    def GET(self,err):
        error=[]
        if int(err)==403:
            error.append('权限不够')
        if int(err)==402:
            error.append('不是作者')
        return render.error(locals(),self)
#其它
class feed(base_view):
    def GET(self):
        articles = session.query(Article).filter_by(published = True).order_by(Article.addTime.desc()).limit(10).all()
        if articles and articles[0]:
            last_updated = articles[0].addTime
            last_updated = last_updated.strftime("%a, %d %b %Y %H:%M:%S +0000")
        for e in articles:
            e.formatted_date = e.addTime.strftime("%a, %d %b %Y %H:%M:%S +0000")
        web.header('Content-type', 'application/rss+xml')
        return render_blog.rss(locals(),self)
        
class redirect:
    def GET(self, path):
        web.seeother('/' + path)

def notfound():
    return web.notfound("Sorry, the '%s' you were looking for was not found."%web.ctx.path)

    # You can use template result like below, either is ok:
    #return web.notfound(render.notfound())
    #return web.notfound(str(render.notfound()))

render_blog = web.template.render('templates/blog/',base='layout',globals={
    'blog':pyblog,
    'category':_category(),
    'newcomment':_newcomment(),
    'tags':_tags(),
    'links':_links(),
    'archives':_archive(),
    'utils':util
})
render_manage = web.template.render('templates/manage/',base='layout',globals={
    'blogtitle':pyblog.blogtitle
})
render=web.template.render('templates/other/')