"""
数据库连接管理模块
"""
import pymysql
import logging
from config.settings import Config

logger = logging.getLogger(__name__)

# 全局数据库连接对象
db_connection = None

def init_database():
    """初始化数据库连接"""
    global db_connection
    
    try:
        db_connection = pymysql.connect(
            host=Config.MYSQL_HOST,
            user=Config.MYSQL_USER,
            password=Config.MYSQL_PASSWORD,
            port=Config.MYSQL_PORT,
            db=Config.MYSQL_DATABASE,
            charset=Config.MYSQL_CHARSET,
            cursorclass=pymysql.cursors.DictCursor
        )
        logger.info("MySQL数据库连接成功")
        return True
    except Exception as e:
        logger.error(f"MySQL数据库连接失败: {str(e)}")
        db_connection = None
        return False

def get_db_connection():
    """获取数据库连接"""
    global db_connection
    
    if db_connection is None:
        init_database()
    
    return db_connection

def close_database():
    """关闭数据库连接"""
    global db_connection
    
    if db_connection:
        db_connection.close()
        db_connection = None
        logger.info("数据库连接已关闭")
