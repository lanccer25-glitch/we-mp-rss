from pydantic import Json
from sqlalchemy import BigInteger

from  .base import Base,Column,String,Integer,DateTime,Text,DATA_STATUS
class ArticleBase(Base):
    """文章基础模型"""
    from_attributes = True
    __tablename__ = 'articles'
    # 文章基础属性
    id = Column(String(255), primary_key=True)  # 文章全局唯一ID（App Message ID / aid）
    mp_id = Column(String(255),index=True)  # 公众号ID
    title = Column(String(1000))  # 文章标题
    pic_url = Column(String(500))  # 封面图片URL地址（对应 cover / cover_img）
    url=Column(String(500))  # 文章的永久链接（URL），用户点击阅读的地址（对应 link）
    description=Column(Text)  # 文章摘要（对应 digest）
    extinfo = Column(Text)  # 扩展信息
    status = Column(Integer,default=1,index=True)  # 文章状态：删除状态标记（对应 is_deleted，false 表示未删除）
    publish_time = Column(Integer,index=True)  # 文章发布时间（对应 update_time，Unix时间戳格式）
    create_time = Column(Integer,index=True)  # 文章创建时间（Unix时间戳格式）
    publish_type = Column(Integer,index=True)  # 发布类型
    publish_src = Column(Integer,index=True)  # 发布来源
    publish_status = Column(Text,index=True)  # 发布状态
    # 状态与类型标识
    original_check_type = Column(Integer,index=True)  # 原创检测类型
    in_profile = Column(Integer,index=True)  # 是否在主页展示
    pre_publish_status = Column(Integer,index=True)  # 预发布状态
    service_type = Column(Integer,index=True)  # 服务类型
    item_show_types = Column(Integer,index=True)  # 展示类型（对应 item_show_type，0通常为普通图文，10可能为特定的无图或特殊样式）
    copyright_stat = Column(Integer,index=True)  # 原创状态（0通常表示非原创，1表示原创）
    has_red_packet_cover = Column(Integer,index=True)  # 封面是否有红包挂件（0为无）
    # 系统字段
    created_at = Column(DateTime)  # 记录创建时间
    updated_at = Column(BigInteger)  # 记录更新时间
    updated_at_millis = Column(BigInteger,index=True)  # 记录更新时间（毫秒）
    is_export = Column(Integer)  # 是否已导出
    is_read = Column(Integer, default=0)  # 是否已读
    is_favorite = Column(Integer, default=0)  # 是否收藏
class Article(ArticleBase):
    content = Column(Text)
    content_html = Column(Text)
    
    def to_dict(self):
        """将Article对象转换为字典"""
        return {
            'id': self.id,
            'mp_id': self.mp_id,
            'title': self.title,
            'pic_url': self.pic_url,
            'url': self.url,
            'description': self.description,
            'content': self.content,
            'content_html': self.content_html,
            'status': self.status,
            'publish_time': self.publish_time,
            'created_at': self.created_at.isoformat() if self.created_at and hasattr(self.created_at, "isoformat") else self.created_at,
            'updated_at': self.updated_at.isoformat() if self.updated_at and hasattr(self.updated_at, "isoformat") else self.updated_at,
            'is_export': self.is_export,
            'is_read': self.is_read,
            'is_favorite': self.is_favorite
        }
