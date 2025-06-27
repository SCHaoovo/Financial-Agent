"""
财务报告系统 Flask 前端应用 - 主路由
"""

import os
from flask import Blueprint, render_template, request, flash, redirect, url_for, send_from_directory, current_app as app
from werkzeug.utils import secure_filename
from flask_frontend.app.utils.file_utils import allowed_file, save_uploaded_file

# 创建蓝图
main_bp = Blueprint('main', __name__)

@main_bp.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@main_bp.route('/upload', methods=['GET', 'POST'])
def upload_files():
    """文件上传页面"""
    if request.method == 'POST':
        # 获取处理类型
        process_type = request.form.get('process_type')
        entity = request.form.get('entity', '')
        financial_year = request.form.get('financial_year', '')
        
        # 验证基本输入
        if not entity or not financial_year:
            flash('请填写实体名称和财务年度', 'error')
            return redirect(request.url)
        
        if not process_type:
            flash('请选择处理方式', 'error')
            return redirect(request.url)
        
        # 验证并保存文件，然后跳转到处理页面
        try:
            saved_files = save_uploaded_files(process_type)
            if saved_files:
                # 跳转到处理页面显示进度
                return redirect(url_for('main.process_files', 
                                      process_type=process_type,
                                      entity=entity,
                                      financial_year=financial_year,
                                      **saved_files))
            else:
                flash('文件上传失败', 'error')
                return redirect(request.url)
                
        except Exception as e:
            app.logger.error(f"文件上传失败: {str(e)}")
            flash(f'上传失败: {str(e)}', 'error')
            return redirect(request.url)
    
    return render_template('upload.html')

def save_uploaded_files(process_type):
    """根据处理类型保存上传的文件"""
    saved_files = {}
    
    if process_type in ['summary', 'workflow']:
        # 需要PL和BS文件
        pl_file = request.files.get('pl_file')
        bs_file = request.files.get('bs_file')
        
        if not pl_file or not bs_file:
            flash('请上传PL表和BS表文件', 'error')
            return None
        
        if not allowed_file(pl_file.filename) or not allowed_file(bs_file.filename):
            flash('请上传有效的Excel文件', 'error')
            return None
        
        # 保存文件
        pl_filename = secure_filename(pl_file.filename)
        bs_filename = secure_filename(bs_file.filename)
        
        pl_path = os.path.join(app.config['UPLOAD_FOLDER'], pl_filename)
        bs_path = os.path.join(app.config['UPLOAD_FOLDER'], bs_filename)
        
        pl_file.save(pl_path)
        bs_file.save(bs_path)
        
        saved_files['pl_file'] = pl_filename
        saved_files['bs_file'] = bs_filename
        
    elif process_type == 'database':
        # 处理动态添加的汇总文件
        summary_filenames = []
        
        # 获取所有上传的文件，无论key名称如何
        app.logger.info(f"请求中的所有文件keys: {list(request.files.keys())}")
        
        for key in request.files.keys():
            files_list = request.files.getlist(key)
            app.logger.info(f"Key '{key}' 包含 {len(files_list)} 个文件")
            
            for file in files_list:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    
                    # 避免重复保存相同文件名的文件
                    if filename not in summary_filenames:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        summary_filenames.append(filename)
                        app.logger.info(f"保存汇总文件: {filename}")
                    else:
                        app.logger.info(f"跳过重复文件: {filename}")
        
        if not summary_filenames:
            flash('没有有效的汇总文件', 'error')
            return None
        
        saved_files['summary_files'] = ','.join(summary_filenames)
        app.logger.info(f"数据库处理保存的文件: {saved_files['summary_files']}")
        
    elif process_type in ['visualization', 'reporting']:
        # 需要数据库文件
        database_file = request.files.get('database_file')
        
        if not database_file:
            flash('请上传数据库文件', 'error')
            return None
        
        if not allowed_file(database_file.filename):
            flash('请上传有效的Excel文件', 'error')
            return None
        
        filename = secure_filename(database_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        database_file.save(file_path)
        
        saved_files['database_file'] = filename
    
    return saved_files

@main_bp.route('/process')
def process_files():
    """处理文件页面 - 显示处理进度"""
    process_type = request.args.get('process_type')
    entity = request.args.get('entity')
    financial_year = request.args.get('financial_year')
    
    if not all([process_type, entity, financial_year]):
        flash('缺少必要的参数', 'error')
        return redirect(url_for('main.upload_files'))
    
    # 获取文件参数
    file_params = {}
    if process_type in ['summary', 'workflow']:
        file_params['pl_file'] = request.args.get('pl_file')
        file_params['bs_file'] = request.args.get('bs_file')
    elif process_type == 'database':
        file_params['summary_files'] = request.args.get('summary_files')
    elif process_type in ['visualization', 'reporting']:
        file_params['database_file'] = request.args.get('database_file')
    
    return render_template('process.html', 
                         process_type=process_type,
                         entity=entity,
                         financial_year=financial_year,
                         **file_params)

@main_bp.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
    try:
        return send_from_directory(app.config['DOWNLOADS_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        from flask import jsonify
        return jsonify({'error': '文件未找到'}), 404

@main_bp.route('/workflow')
def workflow():
    """一体化工作流页面"""
    return render_template('workflow.html')

@main_bp.route('/results')
def results():
    """结果展示页面"""
    return render_template('results.html') 