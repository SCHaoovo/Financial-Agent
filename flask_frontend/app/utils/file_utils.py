"""
财务报告系统 Flask 前端应用 - 文件处理工具
"""

import os
import shutil
from werkzeug.utils import secure_filename
from flask import current_app as app

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

def allowed_file(filename):
    """检查文件扩展名是否被允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, directory=None):
    """保存上传的单个文件
    
    Args:
        file: 上传的文件对象
        directory: 保存目录，默认为app.config['UPLOAD_FOLDER']
        
    Returns:
        str: 保存后的文件名，失败返回None
    """
    if not file or not file.filename:
        return None
        
    if not allowed_file(file.filename):
        return None
        
    filename = secure_filename(file.filename)
    save_dir = directory or app.config['UPLOAD_FOLDER']
    
    # 确保目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, filename)
    file.save(file_path)
    
    return filename

def save_file_content(content, filename, directory=None):
    """保存文件内容
    
    Args:
        content: 文件内容（二进制）
        filename: 文件名
        directory: 保存目录，默认为app.config['DOWNLOADS_FOLDER']
        
    Returns:
        str: 保存后的文件路径
    """
    save_dir = directory or app.config['DOWNLOADS_FOLDER']
    
    # 确保目录存在
    os.makedirs(save_dir, exist_ok=True)
    
    file_path = os.path.join(save_dir, filename)
    
    with open(file_path, 'wb') as f:
        f.write(content)
        
    return file_path

def copy_file(source_path, target_filename, directory=None):
    """复制文件到指定目录
    
    Args:
        source_path: 源文件路径
        target_filename: 目标文件名
        directory: 目标目录，默认为app.config['DOWNLOADS_FOLDER']
        
    Returns:
        str: 目标文件路径，失败返回None
    """
    if not os.path.exists(source_path):
        return None
        
    target_dir = directory or app.config['DOWNLOADS_FOLDER']
    
    # 确保目录存在
    os.makedirs(target_dir, exist_ok=True)
    
    target_path = os.path.join(target_dir, target_filename)
    
    try:
        shutil.copy2(source_path, target_path)
        return target_path
    except Exception as e:
        app.logger.error(f"复制文件失败: {str(e)}")
        return None

def get_file_extension(filename):
    """获取文件扩展名（小写）"""
    return os.path.splitext(filename)[1].lower() if '.' in filename else ''

def detect_file_type(file_content, content_type=None):
    """根据文件内容和Content-Type检测文件类型
    
    Args:
        file_content: 文件内容（二进制）
        content_type: HTTP Content-Type
        
    Returns:
        tuple: (文件类型, 文件扩展名)
    """
    # 检查文件头
    file_header = file_content[:8] if len(file_content) >= 8 else file_content
    
    if file_header.startswith(b'PK\x03\x04'):
        # ZIP文件头（Excel和Word文档都是ZIP格式）
        if b'xl/' in file_content or b'[Content_Types].xml' in file_content:
            # 检查是否包含Excel特有的内容
            if b'xl/workbook.xml' in file_content:
                return 'xlsx', '.xlsx'
            elif b'word/' in file_content or b'document.xml' in file_content:
                return 'docx', '.docx'
            else:
                # 默认为Excel文件
                return 'xlsx', '.xlsx'
        else:
            return 'zip', '.zip'
    elif file_header.startswith(b'\xd0\xcf\x11\xe0'):
        return 'xls', '.xls'
    
    # 根据Content-Type判断
    if content_type:
        if 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
            return 'xlsx', '.xlsx'
        elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
            return 'docx', '.docx'
        elif 'application/zip' in content_type:
            return 'zip', '.zip'
    
    # 默认为Excel
    return 'xlsx', '.xlsx'

def find_file_in_directories(entity, extensions, directories):
    """在多个目录中查找包含特定实体名称且扩展名匹配的文件
    
    Args:
        entity: 实体名称（文件名中应包含的字符串）
        extensions: 文件扩展名列表，如['.xlsx', '.xls']
        directories: 要搜索的目录列表
        
    Returns:
        str: 找到的文件路径，未找到返回None
    """
    for directory in directories:
        if os.path.exists(directory):
            for filename in os.listdir(directory):
                if entity in filename and any(filename.endswith(ext) for ext in extensions):
                    return os.path.join(directory, filename)
    
    return None 