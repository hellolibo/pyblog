#!C:\Python26\python.exe -u
#coding:utf-8
'''
#!/usr/bin/python
#coding:utf-8
'''
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property, hybrid_method
from sqlalchemy.orm import mapper, Session, sessionmaker, backref, relation, relation
from sqlalchemy.schema import MetaData, Table, Column, ForeignKey, Sequence
from sqlalchemy.types import *
from sqlalchemy import or_,and_
from sqlalchemy.sql import func

import pymysql_sa
import datetime
import time
import os
import re
import string
import config
import hashlib
import urllib

pymysql_sa.make_default_mysql_dialect()

db = create_engine(config.DB_PATH,echo=False, encoding='utf8')
#db = create_engine('sqlite:///:memory:', echo=True)
Base = declarative_base()
metadata = Base.metadata

Session = sessionmaker(bind=db)
session = Session()

def now():
    return datetime.datetime.fromtimestamp(time.time())
    #return time.strftime('%Y-%m-%d %X', time.localtime())

class Blog(Base):
    __tablename__ = 'blog'
    
    blogtitle   = Column(String(100), nullable=False,primary_key=True)
    subtitle    = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    createdate  = Column(DateTime, nullable=False, default=now())
    postcount   = Column(Integer,default=0)
    urlpath     = Column(String(255),nullable=False)
    
    def __init__(self, blogtitle=None, subtitle=None, description=None, postcount=0):
        self.blogtitle = blogtitle
        self.subtitle = subtitle
        self.description = description
        self.postcount= postcount
        
    def __repr__(self):
        return "blogtitle=%s, subtitle=%s, description=%s" % (self.blogtitle, self.subtitle, self.description)

aritcle_category = Table('article_category', metadata,
    Column("article_id", Integer,ForeignKey("article.id"),primary_key=True),
    Column("category_id", Integer,ForeignKey("categories.id"),primary_key=True)
)

article_tag = Table("article_tag",metadata,
    Column("article_id",Integer,ForeignKey("article.id"),primary_key=True),
    Column("tag_id",Integer,ForeignKey("tag.id"),primary_key=True)
)

class Aritcle_Category(object):
    pass
class Article_Tag(object):
    pass
    
mapper(Aritcle_Category, aritcle_category)
mapper(Article_Tag, article_tag)

class Tag(Base):
    __tablename__="tag"
    
    id = Column(Integer,primary_key=True)
    tag = Column(String(100),nullable=False, unique=True)
        
    def __init__(self,tag):
        self.tag=tag
    
    @hybrid_property
    def tagcount(self):
        return len(self.posts)
    
    @hybrid_property
    def posts(self):
        if self.article:
            return [art for art in self.article if art.published]
        else:
            return []
    @hybrid_method
    def create(self,tag):
        q_tag = session.query(Tag).filter(Tag.tag==tag).first()
        if q_tag:
            return q_tag
        else:
            return Tag(tag)
            
        

class Article(Base):
    __tablename__="article"
    
    id            = Column(Integer,primary_key=True)
    title         = Column(String(255))
    content       = Column(Text,default='')
    template      = Column(String(255),default='')
    summary       = Column(String(255),default='')
    slug          = Column(String(255),default='')
    published     = Column(Boolean,default=True)
    isTop         = Column(Boolean,default=False)
    isComment     = Column(Boolean,default=True)
    readtimes     = Column(Integer,default=0)
    comment_count = Column(Integer,default=0)
    addTime       = Column(DateTime,default=now())
    modTime       = Column(DateTime,default=now())
    author_id     = Column(Integer,ForeignKey("user.id"))
    author_name   = Column(String(255),default='')
    
    _relateposts  = None

    author = relation("User", backref="article", uselist=False)
    comments = relation("Comment",backref='article')
    categories = relation("Categories", secondary=aritcle_category, backref='article')
    tags = relation("Tag", secondary=article_tag, backref='article')
    
    def __repr__(self):
        return "title=%s" % (Article.title)
        
    @hybrid_property
    def link(self):
        if self.slug:
            return "/%s/%s/%s/%s.html"%(self.addTime.strftime('%Y'),self.addTime.strftime('%m'),self.addTime.strftime('%d'),self.slug)
        else:
            return "/?p=%s"%self.id
            
    @hybrid_property
    def cateids(self):
        if self.categories:
            return [cate.id for cate in self.categories]
        else:
            return []
    
    @hybrid_property
    def tagsStr(self):
        return ",".join([i.tag for i in self.tags if i.tag])
        
        
    @hybrid_property
    def next(self):
        return session.query(Article).filter_by(published=1).order_by(Article.addTime.asc()).filter(Article.addTime>self.addTime).first()
    
    @hybrid_property
    def prev(self):
        return session.query(Article).filter_by(published=1).order_by(Article.addTime.desc()).filter(Article.addTime<self.addTime).first()
        
    @hybrid_property
    def relateposts(self):
        if self._relateposts:
            return self._relateposts
        else:
            if len(self.tags)>0:
                tmp_list = []
                [(lambda x,y:x.extend(y))(tmp_list,t.posts) for t in self.tags if t.tag]
                self._relateposts = [p for p in list(set(tmp_list)) if p.id!=self.id]
            else:
                self._relateposts = []
            return self._relateposts
    
    @hybrid_method
    def delete_comments(self):
        for comment in self.comments:
            comment.delete()
            
        self.comment_count=0
        
    #by microlog
    @hybrid_method
    def update_archive(self,cnt=1):
        my = self.addTime.strftime('%B %Y') #september-2008
        sy = self.addTime.strftime('%Y') #2008
        sm = self.addTime.strftime('%m') #09
        
        archive = session.query(Archive).filter_by(monthyear=my).first()
        
        if not archive:
            archive = Archive(monthyear=my,year=sy,month=sm,articlecount=1)
            session.add(archive)
        else:
            archive.articlecount += cnt

        blog = session.query(Blog).first()
        blog.postcount+=cnt
        
        session.commit()
        
        
class User(Base):
    __tablename__ = "user"
    
    id       = Column(Integer,primary_key=True)
    accountname = Column(String(255),nullable=False)
    password = Column(String(100),nullable=False)
    dispname = Column(String(100),nullable=False)
    email = Column(String(100),nullable=True)
    isadmin=Column(Boolean,nullable=False,default=False)
    
    posts = relation("Article", backref = "user", order_by=Article.id)
    
    def __init__(self, dispname=None, email=None, website=None, isadmin=0):
        self.dispname = dispname
        self.email = email
        self.website = website
        self.isadmin = isadmin
        
    def __repr__(self):
        return "dispname=%s, email=%s, isadmin=%s" % (self.dispname, self.email, self.isadmin)
    
    @hybrid_property
    def post_count(self):
        return session.query(Article).filter_by(author_id=self.id).count()
    
    @hybrid_method
    def add(self):
        session.add(self)
    
class Categories(Base):

    __tablename__='categories'
    
    id = Column(Integer,primary_key=True)
    title = Column(String(255),default='',nullable=False)
    description = Column(Text,default='')
    keyword = Column(Text,default='')
    addTime = Column(DateTime,default=now())
    order = Column(Integer,default=0)
    parent_id = Column(Integer, nullable=True)
    slug = Column(String(255),nullable=False,unique=True)
    
    @hybrid_property
    def level(self):
        return self.getlevel(self,0)
    
    @hybrid_property
    def parentc(self):
        if not self.parent_id or self.parent_id==0:
            return None
        else:
            return session.query(Categories).filter(Categories.id == self.parent_id).first()
        
    @hybrid_property
    def children(self):
        return session.query(Categories).filter(Categories.parent_id == self.id).all()
    
    @hybrid_property
    def posts(self):
        return session.query(Article).filter_by(published=1).filter_by(category_id=self.id).all()
    
    @hybrid_property
    def count(self):
        return len(self.article)
    
    @hybrid_method
    def getlevel(self,cate,lev):
        if cate.parent_id and cate.parent_id != 0:
            lev=self.getlevel(cate.parentc,lev+1)
        return lev
    
    @hybrid_method    
    def haveslug(self,slug):
        if session.query(Categories).filter_by(id!=self.id).filter_by(slug = self.slug).count()==0:
            return False
        else:
            return True
            
class Archive(Base):
    __tablename__="archive"
    
    id=Column(Integer,primary_key=True)
    year = Column(String(45))
    month = Column(String(45))
    monthyear = Column(String(100))
    articlecount = Column(Integer,default=0)
    addTime = Column(DateTime,default=now())
    
class Media(Base):
    __tablename__="media"
    
    id = Column(Integer,primary_key=True)
    name = Column(String(255))
    mtype = Column(String(255))
    url = Column(String(255))
    addTime = Column(DateTime,default=now())
    download = Column(Integer,default=0)
    size = Column(Float,default=0)
    
    def __init__(self,name='',mtype='',url='',size=0):
        self.name=name
        self.mtype=mtype
        self.url=url
        self.size=size
    
class Comment(Base):
    __tablename__="comment"
    
    id = Column(Integer,primary_key=True)
    article_id = Column(Integer,ForeignKey("article.id"))
    author = Column(String(200),nullable=False)
    email = Column(String(200))
    weburl = Column(String(200))
    ip = Column(String(200))
    content = Column(Text,nullable=False)
    addTime  = Column(DateTime,default=now())        
        
    @hybrid_property
    def articlelink(self):
        return self.article and self.article.link 
    
    @hybrid_property
    def shortcontent(self,len=20):
        scontent=self.content
        scontent=re.sub(r'<br\s*/>',' ',scontent)
        scontent=re.sub(r'<[^>]+>','',scontent)
        scontent=re.sub(r'(@[\S]+)-\d{2,7}',r'\1:',scontent)
        return scontent[:len].replace('<','&lt;').replace('>','&gt;')
        
    @hybrid_property
    def gravatar_url(self):
        default = '/static/pic/homsar.jpeg'

        if not self.email:
            return default

        size = 50
        try:
            # construct the url
            imgurl = "http://www.gravatar.com/avatar/"
            imgurl +=hashlib.md5(self.email.lower()).hexdigest()+"?"+ urllib.urlencode({
                'd':default, 's':str(size),'r':'R'})
            return imgurl
        except:
            return default

    @hybrid_method    
    def delit(self):
        self.article.comment_count-=1
        if self.article.comment_count<0:
            self.article.comment_count = 0
        session.delete(self)

class Links(Base):
    __tablename__ = "links"
    
    id = Column(Integer,primary_key=True)
    title = Column(String(200),nullable=False)
    href = Column(String(255),nullable=False)
    remark = Column(String(255))
    addTime = Column(DateTime,default=now())


   
def initBlog():
    global pyblog
    
    pyblog = Blog()
    pyblog.blogtitle='GAE Python Blog '
    pyblog.subtitle='my first gae app'
    pyblog.description='this is test GAE blog'
    pyblog.urlpath="http://"+os.environ['HTTP_HOST']
    
    session.add(pyblog)
    session.commit()
    
    return pyblog
    
def getBlog():
    global pyblog
    try:
       if pyblog:
           return pyblog
    except:
        pass
    pyblog = session.query(Blog).first()
    if not pyblog:
        pyblog=initBlog()
    return pyblog

def intallDB():
    try:
        #metadata.drop_all()
        metadata.create_all(db)
        return True
    except:
       return False
    
try:
    pyblog=getBlog()
except:
    pass
    

if __name__ == "__main__":

    
    #Create db
    metadata.create_all(db)
    
    #Initialization blog
    pyblog = Blog()
    pyblog.blogtitle='GAE Python Blog '
    pyblog.subtitle='my first gae app'
    pyblog.description='this is test GAE blog'
    pyblog.urlpath="http://"
    session.add(pyblog)
    
    #add user
    u = User()
    u.accountname = "libo"
    u.password = hashlib.md5("1").hexdigest()
    u.dispname = "libo"
    u.email = "hellolibo@gmail.com"
    u.isadmin=True
    session.add(u)
    session.commit()

    '''
    #create categories
    cate_a = Categories("blog_cate_a","cate_one")
    cate_b = Categories("blog_cate_b","cate_two")
    
    #create article
    art = Article()
    art.title         = "test"
    art.content       = "test content for pyblog"
    art.summary       = "test content"
    art.slug          = "test"
    
    art.auther        = u
    art.categories.append(cate_a)
    art.categories.append(cate_b)
    session.add(art)
    
   
    art.tags.append(Tag.create("test"))
    art.tags.append(Tag.create("test3"))
    
    art2 = Article()
    art2.title         = "test2"
    art2.content       = "test2 content for pyblog"
    art2.summary       = "test2 content"
    art2.slug          = "test2"
    
    art2.auther        = u
    art2.categories.append(cate_a)
    session.add(art2)
    
    art2.tags.append(Tag.create("test3"))
    art2.tags.append(Tag.create("test4"))
    
    #create comment
    art.comments.append(Comment("A","It's best!","hellolibo@gmail.com"))
    
    session.commit()
    
    #tag count
    tag_count_subquery = session.query(Article_Tag.tag_id, func.count('*').label('tag_count')).group_by(Article_Tag.tag_id).subquery()
    
    abc = session.query(Tag, tag_count_subquery.c.tag_count).join((tag_count_subquery, Tag.id==tag_count_subquery.c.tag_id)).order_by(tag_count_subquery.c.tag_count.desc()).all()
    
    print [(a.tag,b) for a,b in abc]
    
    '''
    
    

   