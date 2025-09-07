"""
知识图谱服务模块
负责中文分词、数据库查询和知识检索功能
"""
import jieba
import csv
import pymysql.cursors
import pymysql
import logging
import os
from config.database import get_db_connection
from config.settings import Config

logger = logging.getLogger(__name__)

class KnowledgeService:
    """知识图谱服务"""
    
    def __init__(self):
        self.stopwords = self._load_stopwords()
        self.db_connection = None
        self._init_database()
    
    def _init_database(self):
        """初始化数据库连接"""
        try:
            self.db_connection = pymysql.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                port=Config.MYSQL_PORT,
                db=Config.MYSQL_DATABASE,
                charset=Config.MYSQL_CHARSET,
                cursorclass=pymysql.cursors.DictCursor
            )
            logger.info("MySQL数据库连接成功")
        except Exception as e:
            logger.error(f"MySQL数据库连接失败: {str(e)}")
            self.db_connection = None
    
    def _load_stopwords(self):
        """导入停用词"""
        try:
            stopwords_file = Config.BASE_DIR / "config" / "cn_stopwords.txt"
            if stopwords_file.exists():
                with open(stopwords_file, encoding="utf-8") as f:
                    stopwords = [line.strip() for line in f.readlines()]
                logger.info(f"加载了 {len(stopwords)} 个停用词")
                return stopwords
            else:
                logger.warning("停用词文件未找到，返回空列表")
                return []
        except Exception as e:
            logger.error(f"加载停用词失败: {str(e)}")
            return []
    
    def _sql_query(self, keyword):
        """数据库查询操作"""
        if self.db_connection is None:
            logger.error("数据库未连接，无法执行查询")
            return []
        
        try:
            with self.db_connection.cursor() as cursor:
                query_space = """
                select distinct CID,Cname,Cnumber,Cclass,Cparty,ClawRe,CP,CP1,CP2,CP3,CP4,Ckey,Cmain,Cindex,CB1,CB2 
                from 特种设备安全法规 
                where Cindex like '%{keyword}%' or Ckey like '%{keyword}%' or Cmain like '%{keyword}%'
                """
                sql = query_space.format(keyword=keyword)
                cursor.execute(sql)
                result = cursor.fetchall()
                
            # 生成CSV文件
            csv_path = Config.BASE_DIR / 'data.csv'
            with open(csv_path, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['source', 'relation', 'target'])
                for i in result:
                    if i.get('CP') != '' and i.get('Cname') != '':
                        writer.writerow([i.get('CP'), '章', i.get('Cname')])
                    if i.get('CP') != '' and i.get('CP1') != '':
                        writer.writerow([i.get('CP'), '一级节', i.get('CP1')])
                    if i.get('CP1') != '' and i.get('CP2') != '':
                        writer.writerow([i.get('CP2'), '二级节', i.get('CP1')])
                    if i.get('CP2') != '' and i.get('CP3') != '':
                        writer.writerow([i.get('CP2'), '三级节', i.get('CP3')])
                    if i.get('CP3') != '' and i.get('CP4') != '':
                        writer.writerow([i.get('CP4'), '四级节', i.get('CP3')])
                
                # 调用知识图谱创建函数
                self._kg_creat(str(csv_path))
                return result
        except Exception as e:
            logger.error(f"SQL查询执行失败: {str(e)}")
            return []
    
    def _sql_query_hot_search(self, keyword1=None):
        """热搜查询"""
        if self.db_connection is None:
            logger.error("数据库未连接，无法执行热搜查询")
            return []
        
        try:
            with self.db_connection.cursor() as cursor:
                sql = "select * from 热搜"
                cursor.execute(sql)
                result = cursor.fetchall()
                return result
        except Exception as e:
            logger.error(f"热搜查询执行失败: {str(e)}")
            return []
    
    def _insert_hot_search(self, value):
        """插入热搜数据"""
        if self.db_connection is None:
            logger.error("数据库未连接，无法插入热搜数据")
            return
        
        try:
            cursor = self.db_connection.cursor()
            sql = "INSERT INTO 热搜(字段) values(%s)"
            cursor.execute(sql, value)
            self.db_connection.commit()
            logger.info('插入热搜数据成功')
        except Exception as e:
            self.db_connection.rollback()
            logger.error(f"插入热搜数据失败: {str(e)}")
    
    def _kg_creat(self, csv_file):
        """知识图谱创建函数（简化实现）"""
        try:
            logger.info(f"调用了知识图谱创建，CSV文件: {csv_file}")
            # 这里可以集成实际的知识图谱创建逻辑
            # 目前提供简化实现
        except Exception as e:
            logger.error(f"知识图谱创建失败: {str(e)}")
    
    def _re_duo(self, data):
        """去重实现"""
        try:
            unique_data = []
            seen = set()
            for item in data:
                if isinstance(item, dict):
                    item_tuple = tuple(sorted(item.items()))
                    if item_tuple not in seen:
                        seen.add(item_tuple)
                        unique_data.append(item)
                else:
                    if item not in seen:
                        seen.add(item)
                        unique_data.append(item)
            return unique_data
        except Exception as e:
            logger.error(f"去重处理失败: {str(e)}")
            return data
    
    def _re_sou(self, data):
        """排序实现"""
        try:
            if not data:
                return data
            # 尝试按字段排序，如果没有则保持原顺序
            return sorted(data, key=lambda x: x.get('字段', '') if isinstance(x, dict) else str(x))
        except Exception as e:
            logger.error(f"排序处理失败: {str(e)}")
            return data
    
    def search_knowledge(self, keyword):
        """知识图谱搜索"""
        try:
            # 分词处理
            sentence_depart = jieba.cut(keyword.strip())
            
            # 过滤停用词
            outstr = ""
            for word in sentence_depart:
                if word not in self.stopwords:
                    if word != "\t" and word != " ":
                        outstr += word
                        outstr += ""  # 与app_7.py一致
            
            # 搜索结果
            search_result = []
            resou = []
            
            # 分词搜索
            cut_keywords = jieba.cut_for_search(outstr)
            cut_keyword1 = jieba.cut_for_search(outstr)
            
            for cut_keyword in cut_keyword1:
                value = cut_keyword
                self._insert_hot_search(value)
                resou = self._sql_query_hot_search()
                
                # 执行查询
                search_result.extend(self._sql_query(cut_keyword))
            
            # 处理热搜结果
            resou_result = self._re_sou(resou)
            
            # 去重与排序
            search_result = self._re_duo(search_result)
            
            # 记录搜索结果数量
            search_nums = len(search_result)
            
            return {
                "success": True,
                "search_result": search_result,
                "search_nums": search_nums,
                "keyword": keyword,
                "hotSearch": resou_result,
                "hotSearchRank": [{"key": f"Top{i+1}"} for i in range(7)]
            }
            
        except Exception as e:
            logger.error(f"知识搜索失败: {str(e)}")
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}"
            }
    
    def get_hot_search(self):
        """获取热搜数据"""
        try:
            resou = self._sql_query_hot_search()
            resou_result = self._re_sou(resou)
            
            return {
                "success": True,
                "hotSearch": resou_result,
                "hotSearchRank": [{"key": f"Top{i+1}"} for i in range(7)]
            }
        except Exception as e:
            logger.error(f"获取热搜数据失败: {str(e)}")
            return {
                "success": False,
                "error": f"获取热搜失败: {str(e)}"
            }

# 全局服务实例
knowledge_service = KnowledgeService()