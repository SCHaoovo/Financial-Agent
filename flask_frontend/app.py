"""
财务报告系统 Flask 前端应用
"""

import os
import requests
from flask import Flask, render_template, request, flash, redirect, url_for, send_file, jsonify, send_from_directory
from flask_cors import CORS
from werkzeug.utils import secure_filename
import logging
import shutil
from datetime import datetime
import time
from pathlib import Path
from src.config import get_settings

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 创建Flask应用
app = Flask(__name__)

# 配置密钥
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

# 获取配置设置
settings = get_settings()

# 环境感知的目录配置
if os.getenv('ENVIRONMENT') == 'production':
    # Render.com 生产环境
    base_dir = Path('/tmp/financial_app')
    app.config['UPLOAD_FOLDER'] = str(base_dir / 'uploads')
    app.config['DOWNLOADS_FOLDER'] = str(base_dir / 'downloads')
else:
    # 本地开发环境
    app.config['UPLOAD_FOLDER'] = 'uploads'
    app.config['DOWNLOADS_FOLDER'] = 'downloads'

app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB 最大文件大小

# 启用CORS支持
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5000", "http://127.0.0.1:5000"],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

# 允许的文件扩展名
ALLOWED_EXTENSIONS = {'xlsx', 'xls'}

# FastAPI后端的基础URL
BACKEND_URL = os.environ.get('BACKEND_URL', 'http://localhost:8000')


# 创建必要的目录
def ensure_directories():
    """确保必要的目录存在"""
    directories = [
        app.config['UPLOAD_FOLDER'],
        app.config['DOWNLOADS_FOLDER']
    ]

    for directory in directories:
        try:
            if not os.path.exists(directory):
                os.makedirs(directory, exist_ok=True)
                logger.info(f"目录已创建: {directory}")
            else:
                logger.info(f"目录已存在: {directory}")
        except Exception as e:
            logger.error(f"创建目录失败 {directory}: {str(e)}")
            # 在云环境中，目录创建失败不应该阻止应用启动
            pass


# 初始化目录
ensure_directories()


def allowed_file(filename):
    """检查文件扩展名是否被允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')


@app.route('/upload', methods=['GET', 'POST'])
def upload_files():
    """文件上传页面"""
    if request.method == 'POST':
        # 获取处理类型
        process_type = request.form.get('process_type')
        entity = request.form.get('entity', '')
        financial_year = request.form.get('financial_year', '')

        # Validate basic input
        if not entity:
            flash('Please fill in entity name', 'error')
            return redirect(request.url)

        # 只有summary和workflow需要financial_year
        if process_type in ['summary', 'workflow'] and not financial_year:
            flash('Please fill in financial year for summary and workflow processing', 'error')
            return redirect(request.url)

        if not process_type:
            flash('Please select processing method', 'error')
            return redirect(request.url)

        # 验证并保存文件，然后跳转到处理页面
        try:
            saved_files = save_uploaded_files(process_type)
            if saved_files:
                # 跳转到处理页面显示进度
                return redirect(url_for('process_files',
                                        process_type=process_type,
                                        entity=entity,
                                        financial_year=financial_year,
                                        **saved_files))
            else:
                flash('File upload failed', 'error')
                return redirect(request.url)

        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            flash(f'Upload failed: {str(e)}', 'error')
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
            flash('Please upload PL and BS files', 'error')
            return None

        if not allowed_file(pl_file.filename) or not allowed_file(bs_file.filename):
            flash('Please upload valid Excel files', 'error')
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
        logger.info(f"请求中的所有文件keys: {list(request.files.keys())}")

        for key in request.files.keys():
            files_list = request.files.getlist(key)
            logger.info(f"Key '{key}' 包含 {len(files_list)} 个文件")

            for file in files_list:
                if file and file.filename and allowed_file(file.filename):
                    filename = secure_filename(file.filename)

                    # 避免重复保存相同文件名的文件
                    if filename not in summary_filenames:
                        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                        file.save(file_path)
                        summary_filenames.append(filename)
                        logger.info(f"保存汇总文件: {filename}")
                    else:
                        logger.info(f"跳过重复文件: {filename}")

        if not summary_filenames:
            flash('No valid summary files found', 'error')
            return None

        saved_files['summary_files'] = ','.join(summary_filenames)
        logger.info(f"数据库处理保存的文件: {saved_files['summary_files']}")

    elif process_type in ['visualization', 'reporting']:
        # 需要数据库文件
        database_file = request.files.get('database_file')

        if not database_file:
            flash('Please upload database file', 'error')
            return None

        if not allowed_file(database_file.filename):
            flash('Please upload valid Excel file', 'error')
            return None

        filename = secure_filename(database_file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        database_file.save(file_path)

        saved_files['database_file'] = filename

    return saved_files


def handle_summary_output_file(output_file, entity, financial_year, result):
    """处理汇总生成的输出文件"""
    try:
        logger.info(f"处理汇总输出文件: {output_file}")

        # 生成本地文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        original_filename = os.path.basename(output_file)
        file_extension = os.path.splitext(original_filename)[1].lower()
        
        if file_extension == '.docx':
            local_filename = f"Summary_{entity}_{financial_year}.docx"
            file_type = 'docx'
        elif file_extension == '.xlsx':
            local_filename = f"Summary_{entity}_{financial_year}.xlsx"
            file_type = 'xlsx'
        else:
            # 默认为Excel格式
            local_filename = f"Summary_{entity}_{financial_year}.xlsx"
            file_type = 'xlsx'
        
        local_path = os.path.join(app.config['DOWNLOADS_FOLDER'], local_filename)

        # 确保下载目录存在
        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)

        # 检查文件是否存在
        if os.path.exists(output_file):
            # 复制文件到下载目录
            shutil.copy2(output_file, local_path)
            logger.info(f"汇总文件已保存到: {local_path}")

            # 验证复制的文件
            if os.path.exists(local_path) and os.path.getsize(local_path) > 0:
                return jsonify({
                    'success': True,
                    'message': f'汇总生成成功！文件已保存为 {local_filename}',
                    'download_url': url_for('download_file', filename=local_filename),
                    'file_type': file_type,
                    'result': result
                })
            else:
                logger.error("复制的文件为空或不存在")
                return jsonify({
                    'success': False,
                    'message': '生成的文件为空'
                }), 500
        else:
            # 在预期目录中搜索类似文件
            search_dirs = [
                os.path.dirname(output_file),
                app.config['DOWNLOADS_FOLDER'],
                settings.PROCESSED_DATA_DIR + '/summary',
                os.path.join(settings.PROCESSED_DATA_DIR, 'summary')
            ]

            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for file in os.listdir(search_dir):
                        if entity in file and file.endswith(('.xlsx', '.xls', '.docx')):
                            found_path = os.path.join(search_dir, file)
                            # 检查文件修改时间（最近5分钟内）
                            if time.time() - os.path.getmtime(found_path) < 300:
                                shutil.copy2(found_path, local_path)
                                logger.info(f"找到并复制了汇总文件: {found_path} -> {local_path}")
                                return jsonify({
                                    'success': True,
                                    'message': f'汇总生成成功！文件已保存为 {local_filename}',
                                    'download_url': url_for('download_file', filename=local_filename),
                                    'file_type': file_type,
                                    'result': result
                                })

            # 未找到文件
            logger.warning(f"汇总文件未找到: {output_file}")
            return jsonify({
                'success': True,
                'message': '汇总生成完成，但文件保存位置未确定',
                'result': result
            })

    except Exception as e:
        logger.error(f"处理汇总输出文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'文件处理失败: {str(e)}'
        }), 500


@app.route('/process')
def process_files():
    """处理文件页面 - 显示处理进度"""
    process_type = request.args.get('process_type')
    entity = request.args.get('entity')
    financial_year = request.args.get('financial_year')

    # 基本参数验证
    if not process_type or not entity:
        flash('Missing required parameters', 'error')
        return redirect(url_for('upload_files'))
    
    # 只有summary和workflow需要financial_year
    if process_type in ['summary', 'workflow'] and not financial_year:
        flash('Financial year is required for summary and workflow processing', 'error')
        return redirect(url_for('upload_files'))

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


@app.route('/download/<filename>')
def download_file(filename):
    """下载文件"""
    try:
        return send_from_directory(app.config['DOWNLOADS_FOLDER'], filename, as_attachment=True)
    except FileNotFoundError:
        return "File not found", 404


@app.route('/uploads/<filename>')
def serve_upload_file(filename):
    """提供已上传文件的访问"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    except FileNotFoundError:
        return "File not found", 404


@app.route('/workflow')
def workflow():
    """一体化工作流页面"""
    return render_template('workflow.html')


@app.route('/results')
def results():
    """结果展示页面"""
    return render_template('results.html')


@app.route('/api/generate_summary', methods=['POST'])
def api_generate_summary():
    """调用后端API生成汇总"""
    try:
        logger.info("=== 开始处理summary请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")
        logger.info(f"Request form: {dict(request.form)}")
        logger.info(f"Request files: {list(request.files.keys())}")

        # 同时支持表单数据和JSON数据
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = {
                'pl_file': request.form.get('pl_file'),
                'bs_file': request.form.get('bs_file'),
                'entity': request.form.get('entity'),
                'financial_year': request.form.get('financial_year')
            }
            logger.info(f"表单数据: {data}")

        pl_file = data.get('pl_file')
        bs_file = data.get('bs_file')
        entity = data.get('entity')
        financial_year = data.get('financial_year')

        logger.info(
            f"解析后的参数: pl_file={pl_file}, bs_file={bs_file}, entity={entity}, financial_year={financial_year}")

        # 验证必要参数
        if not pl_file or not bs_file:
            logger.error(f"文件名验证失败: pl_file={pl_file}, bs_file={bs_file}")
            return jsonify({
                'success': False,
                'message': 'Please provide PL and BS file names'
            }), 400

        if not entity or not financial_year:
            logger.error(f"实体信息验证失败: entity={entity}, financial_year={financial_year}")
            return jsonify({
                'success': False,
                'message': 'Please provide entity name and financial year'
            }), 400

        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # 构建文件路径
        pl_path = os.path.join(app.config['UPLOAD_FOLDER'], pl_file)
        bs_path = os.path.join(app.config['UPLOAD_FOLDER'], bs_file)

        # 检查文件是否存在
        if not os.path.exists(pl_path):
            logger.error(f"PL文件不存在: {pl_path}")
            return jsonify({
                'success': False,
                'message': f'PL file not found: {pl_file}'
            }), 400

        if not os.path.exists(bs_path):
            logger.error(f"BS文件不存在: {bs_path}")
            return jsonify({
                'success': False,
                'message': f'BS file not found: {bs_file}'
            }), 400

        logger.info(f"文件存在验证通过: PL={pl_path}, BS={bs_path}")

        # 准备multipart/form-data请求
        with open(pl_path, 'rb') as pl_f, open(bs_path, 'rb') as bs_f:
            files = {
                'pl_file': (pl_file, pl_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                'bs_file': (bs_file, bs_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data_form = {
                'entity': entity,
                'financial_year': financial_year
            }

            logger.info(f"准备调用后端API: {BACKEND_URL}/finance/summary/generate")
            logger.info(f"请求参数: {data_form}")

            # 调用FastAPI后端
            backend_response = requests.post(
                f'{BACKEND_URL}/finance/summary/generate',
                files=files,
                data=data_form,
                timeout=900  # Increased from 300 to 900 seconds (15 minutes)
            )

        logger.info(f"后端响应状态码: {backend_response.status_code}")
        logger.info(f"后端响应内容类型: {backend_response.headers.get('content-type')}")

        if backend_response.status_code == 200:
            # 检查响应内容类型
            content_type = backend_response.headers.get('content-type', '')
            logger.info(f"响应内容类型: {content_type}")
            logger.info(f"响应内容长度: {len(backend_response.content)}")

            # 首先尝试解析为JSON
            try:
                result = backend_response.json()
                logger.info(f"JSON响应解析成功: {result}")

                # 查找文件路径信息
                file_path_in_response = None
                possible_keys = ['file_path', 'output_file', 'summary_file', 'result_file']

                for key in possible_keys:
                    if key in result and result[key]:
                        file_path_in_response = result[key]
                        logger.info(f"从JSON响应中找到文件路径 ({key}): {file_path_in_response}")
                        break

                # 如果JSON中没有直接的文件路径，检查是否有嵌套结构
                if not file_path_in_response and 'message' in result:
                    message = result['message']
                    # 从日志消息中提取文件路径
                    if '已成功保存汇总文件:' in message:
                        import re
                        path_match = re.search(r'已成功保存汇总文件:\s*([^\s,，]+)', message)
                        if path_match:
                            file_path_in_response = path_match.group(1).strip()
                            logger.info(f"从消息中提取的文件路径: {file_path_in_response}")

                # 如果找到了文件路径，尝试复制文件
                if file_path_in_response:
                    logger.info(f"准备处理文件: {file_path_in_response}")

                    if os.path.exists(file_path_in_response):
                        logger.info(f"找到生成的文件: {file_path_in_response}")

                        filename = f"Summary_{entity}_{financial_year}.xlsx"
                        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
                        downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                        try:
                            shutil.copy2(file_path_in_response, downloads_path)
                            logger.info(f"文件已从 {file_path_in_response} 复制到 {downloads_path}")

                            if os.path.exists(downloads_path) and os.path.getsize(downloads_path) > 0:
                                return jsonify({
                                    'success': True,
                                    'message': '汇总生成成功！',
                                    'download_url': url_for('download_file', filename=filename),
                                    'file_type': 'xlsx',
                                    'original_path': file_path_in_response
                                })
                            else:
                                logger.error("复制的文件为空或不存在")
                                return jsonify({
                                    'success': False,
                                    'message': '生成的文件为空'
                                }), 500
                        except Exception as e:
                            logger.error(f"复制文件失败: {str(e)}")
                            return jsonify({
                                'success': False,
                                'message': f'复制文件失败: {str(e)}'
                            }), 500
                    else:
                        logger.error(f"指定的文件路径不存在: {file_path_in_response}")

                        # 尝试在预期的目录中查找文件
                        expected_dirs = [
                            settings.PROCESSED_DATA_DIR + '/summary',
                            os.path.join(settings.PROCESSED_DATA_DIR, 'summary'),
                            app.config['DOWNLOADS_FOLDER']
                        ]

                        found_file = None
                        for search_dir in expected_dirs:
                            logger.info(f"搜索目录: {search_dir}")
                            if os.path.exists(search_dir):
                                for filename in os.listdir(search_dir):
                                    if entity in filename and filename.endswith(('.docx', '.xlsx')):
                                        found_file = os.path.join(search_dir, filename)
                                        logger.info(f"找到匹配文件: {found_file}")
                                        return handle_summary_output_file(found_file, entity, financial_year, result)

                        if found_file:
                            logger.info(f"使用搜索到的文件: {found_file}")
                            return handle_summary_output_file(found_file, entity, financial_year, result)
                        else:
                            # 尝试在预期的目录中查找文件
                            expected_dirs = [
                                settings.PROCESSED_DATA_DIR + '/summary',
                                os.path.join(settings.PROCESSED_DATA_DIR, 'summary'),
                                app.config['DOWNLOADS_FOLDER']
                            ]

                            for search_dir in expected_dirs:
                                logger.info(f"搜索目录: {search_dir}")
                                if os.path.exists(search_dir):
                                    for filename in os.listdir(search_dir):
                                        if entity in filename and filename.endswith(('.docx', '.xlsx')):
                                            found_file = os.path.join(search_dir, filename)
                                            logger.info(f"找到匹配文件: {found_file}")
                                            return handle_summary_output_file(found_file, entity, financial_year,
                                                                              result)

                # 如果没有找到文件路径，返回JSON结果
                return jsonify({
                    'success': True,
                    'message': '汇总处理完成',
                    'result': result
                })

            except ValueError as json_error:
                logger.warning(f"响应不是JSON格式: {str(json_error)}")
                pass

            # 检查响应内容是否为空
            if len(backend_response.content) == 0:
                logger.error("后端返回空内容")
                return jsonify({
                    'success': False,
                    'message': '后端返回空文件'
                }), 500

            # 作为二进制文件处理
            logger.info("将响应作为二进制文件处理")

            # 根据文件头判断文件类型
            file_header = backend_response.content[:8] if len(
                backend_response.content) >= 8 else backend_response.content
            logger.info(f"文件头部信息: {file_header}")

            # 汇总文件通常是Excel格式
            filename = f"Summary_{entity}_{financial_year}.xlsx"
            file_type = 'xlsx'

            if file_header.startswith(b'PK\x03\x04'):
                if b'xl/workbook.xml' in backend_response.content:
                    logger.info("检测到Excel文件格式")
                else:
                    logger.info("检测到ZIP格式，默认为Excel")
            elif file_header.startswith(b'\xd0\xcf\x11\xe0'):
                filename = f"Summary_{entity}_{financial_year}.xls"
                file_type = 'xls'
                logger.info("检测到旧版Excel文件格式")
            else:
                logger.info("使用默认Excel格式")

            # 保存文件
            file_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
            try:
                with open(file_path, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"文件已保存到: {file_path}")

                file_size = os.path.getsize(file_path)
                logger.info(f"保存的文件大小: {file_size} 字节")

                if file_size == 0:
                    logger.error("保存的文件大小为0")
                    return jsonify({
                        'success': False,
                        'message': '生成的文件为空'
                    }), 500

                return jsonify({
                    'success': True,
                    'message': '汇总文件已生成！',
                    'download_url': url_for('download_file', filename=filename),
                    'file_type': file_type
                })

            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'保存文件失败: {str(e)}'
                }), 500
        else:
            logger.error(f"后端处理失败: {backend_response.status_code}, {backend_response.text}")
            return jsonify({
                'success': False,
                'message': f'后端处理失败: {backend_response.text}'
            }), 500

    except requests.Timeout:
        logger.error("Request timeout")
        return jsonify({
            'success': False,
            'message': 'Processing timeout, please try again later'
        }), 500
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Processing failed: {str(e)}'
        }), 500


@app.route('/api/generate_database', methods=['POST'])
def api_generate_database():
    """调用后端API生成数据库"""
    try:
        logger.info("=== 开始处理database请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request form: {dict(request.form)}")
        logger.info(f"Request files keys: {list(request.files.keys())}")

        # 获取表单数据
        entity = request.form.get('entity')
        financial_year = request.form.get('financial_year')
        summary_files_param = request.form.get('summary_files')  # 文件名字符串

        logger.info(f"Entity: {entity}, Financial Year: {financial_year}")
        logger.info(f"Summary files parameter: {summary_files_param}")

        # 验证必要参数 - 只需要entity，financial_year是可选的
        if not entity:
            logger.error("缺少必要参数: entity")
            return jsonify({
                'success': False,
                'message': 'Missing required parameters: entity'
            }), 400

        # 处理summary_files参数
        summary_files_list = []

        # 优先处理上传的文件
        uploaded_files = request.files.getlist('summary_files')
        if uploaded_files:
            logger.info(f"接收到直接上传的文件: {len(uploaded_files)}")
            for file in uploaded_files:
                if file and file.filename and allowed_file(file.filename):
                    summary_files_list.append(file)
                    logger.info(f"有效上传文件: {file.filename}")

        # 如果没有直接上传的文件，处理文件名参数
        elif summary_files_param:
            logger.info("处理文件名参数，从uploads目录读取文件")
            filenames = [name.strip() for name in summary_files_param.split(',') if name.strip()]
            logger.info(f"需要读取的文件: {filenames}")

            for filename in filenames:
                if allowed_file(filename):
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        logger.info(f"找到文件: {file_path}")
                        summary_files_list.append(file_path)
                    else:
                        logger.error(f"文件不存在: {file_path}")
                        return jsonify({
                            'success': False,
                            'message': f'汇总文件不存在: {filename}'
                        }), 400
                else:
                    logger.error(f"无效文件类型: {filename}")
                    return jsonify({
                        'success': False,
                        'message': f'无效文件类型: {filename}'
                    }), 400
        else:
            logger.error("未提供汇总文件")
            return jsonify({
                'success': False,
                'message': 'Please provide at least one summary file'
            }), 400

        if not summary_files_list:
            return jsonify({
                'success': False,
                'message': '没有有效的汇总文件'
            }), 400

        logger.info(f"准备发送 {len(summary_files_list)} 个文件到后端")

        # 准备发送给后端的文件列表
        files_for_backend = []

        try:
            # 处理文件列表
            for i, file_item in enumerate(summary_files_list):
                if isinstance(file_item, str):
                    # 文件路径
                    filename = os.path.basename(file_item)
                    logger.info(f"准备发送文件路径 {i + 1}: {filename}")

                    with open(file_item, 'rb') as f:
                        files_for_backend.append((
                            'summary_files',
                            (filename, f.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                        ))
                else:
                    # 上传的文件对象
                    filename = secure_filename(file_item.filename)
                    logger.info(f"准备发送上传文件 {i + 1}: {filename}")

                    file_item.seek(0)
                    files_for_backend.append((
                        'summary_files',
                        (
                        filename, file_item.read(), 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
                    ))

            # 准备表单数据
            form_data = {
                'entity': entity
            }

            logger.info(f"准备调用后端API: {BACKEND_URL}/finance/database/generate-database")
            logger.info(f"表单参数: {form_data}")
            logger.info(f"文件列表长度: {len(files_for_backend)}")

            # 调用FastAPI后端
            backend_response = requests.post(
                f'{BACKEND_URL}/finance/database/generate-database',
                files=files_for_backend,
                data=form_data,
                timeout=900  # Increased from 300 to 900 seconds (15 minutes)
            )

            logger.info(f"后端响应状态码: {backend_response.status_code}")
            logger.info(f"后端响应内容类型: {backend_response.headers.get('content-type')}")

            if backend_response.status_code == 200:
                # 尝试解析JSON响应
                try:
                    result = backend_response.json()
                    logger.info(f"JSON响应: {result}")

                    # 查找输出文件路径
                    output_file = None
                    for key in ['file_path', 'output_file', 'database_file', 'result_file']:
                        if key in result and result[key]:
                            output_file = result[key]
                            break

                    # 从消息中提取文件路径（备用方案）
                    if not output_file and 'message' in result:
                        import re
                        match = re.search(r'已成功保存数据库文件:\s*([^\s,，]+)', result['message'])
                        if match:
                            output_file = match.group(1).strip()

                    if output_file:
                        # 处理输出文件
                        return handle_database_output_file(output_file, entity, financial_year, result)
                    else:
                        # 没有文件路径，返回基本成功响应
                        return jsonify({
                            'success': True,
                            'message': '数据库生成完成',
                            'result': result
                        })

                except ValueError:
                    # 响应不是JSON，可能是直接的文件内容
                    logger.info("响应不是JSON格式，作为二进制文件处理")
                    return handle_database_binary_response(backend_response, entity, financial_year)

            else:
                error_msg = backend_response.text
                logger.error(f"后端处理失败: {backend_response.status_code}, {error_msg}")
                return jsonify({
                    'success': False,
                    'message': f'后端处理失败: {error_msg}'
                }), backend_response.status_code

        except requests.Timeout:
            logger.error("请求超时")
            return jsonify({
                'success': False,
                'message': '处理超时，请稍后重试'
            }), 500

    except Exception as e:
        logger.error(f"数据库生成API调用失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'处理失败: {str(e)}'
        }), 500


def handle_database_output_file(output_file, entity, financial_year, result):
    """处理数据库生成的输出文件"""
    try:
        logger.info(f"处理输出文件: {output_file}")

        # 生成本地文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"database_{entity}_{financial_year}_{timestamp}.xlsx"
        local_path = os.path.join(app.config['DOWNLOADS_FOLDER'], local_filename)

        # 确保下载目录存在
        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)

        # 检查文件是否存在
        if os.path.exists(output_file):
            # 复制文件到下载目录
            shutil.copy2(output_file, local_path)
            logger.info(f"数据库文件已保存到: {local_path}")

            return jsonify({
                'success': True,
                'message': f'数据库生成成功！文件已保存为 {local_filename}',
                'download_url': url_for('download_file', filename=local_filename),
                'file_type': 'xlsx',
                'result': result
            })
        else:
            # 在预期目录中搜索类似文件
            search_dirs = [
                os.path.dirname(output_file),
                app.config['DOWNLOADS_FOLDER'],
                settings.PROCESSED_DATA_DIR + '/database',
                os.path.join(settings.PROCESSED_DATA_DIR, 'database')
            ]

            for search_dir in search_dirs:
                if os.path.exists(search_dir):
                    for file in os.listdir(search_dir):
                        if 'database' in file.lower() and file.endswith(('.xlsx', '.xls')):
                            found_path = os.path.join(search_dir, file)
                            # 检查文件修改时间（最近5分钟内）
                            if time.time() - os.path.getmtime(found_path) < 300:
                                shutil.copy2(found_path, local_path)
                                logger.info(f"找到并复制了数据库文件: {found_path} -> {local_path}")
                                return jsonify({
                                    'success': True,
                                    'message': f'数据库生成成功！文件已保存为 {local_filename}',
                                    'download_url': url_for('download_file', filename=local_filename),
                                    'file_type': 'xlsx',
                                    'result': result
                                })

            # 未找到文件
            logger.warning(f"数据库文件未找到: {output_file}")
            return jsonify({
                'success': True,
                'message': '数据库生成完成，但文件保存位置未确定',
                'result': result
            })

    except Exception as e:
        logger.error(f"处理数据库输出文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'文件处理失败: {str(e)}'
        }), 500


def handle_database_binary_response(response, entity, financial_year):
    """处理数据库生成的二进制响应"""
    try:
        logger.info("处理二进制文件响应")

        # 生成本地文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        local_filename = f"database_{entity}_{financial_year}_{timestamp}.xlsx"
        local_path = os.path.join(app.config['DOWNLOADS_FOLDER'], local_filename)

        # 确保下载目录存在
        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)

        # 保存文件内容
        with open(local_path, 'wb') as f:
            f.write(response.content)

        logger.info(f"数据库文件已保存到: {local_path}")

        return jsonify({
            'success': True,
            'message': f'数据库生成成功！文件已保存为 {local_filename}',
            'download_url': url_for('download_file', filename=local_filename),
            'file_type': 'xlsx'
        })

    except Exception as e:
        logger.error(f"保存数据库文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'文件保存失败: {str(e)}'
        }), 500


@app.route('/api/generate_visualization', methods=['POST'])
def api_generate_visualization():
    """调用后端API生成可视化"""
    try:
        logger.info("=== 开始处理visualization请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")

        # 同时支持表单数据和JSON数据
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = {
                'database_file': request.form.get('database_file'),
                'entity': request.form.get('entity'),
                'financial_year': request.form.get('financial_year')
            }
            logger.info(f"表单数据: {data}")

        database_file = data.get('database_file')
        entity = data.get('entity')
        financial_year = data.get('financial_year')

        logger.info(f"解析后的参数: database_file={database_file}, entity={entity}, financial_year={financial_year}")

        if not database_file:
            logger.error("未提供数据库文件")
            return jsonify({
                'success': False,
                'message': 'Please provide database file'
            }), 400

        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], database_file)
        if not os.path.exists(file_path):
            logger.error(f"数据库文件不存在: {file_path}")
            return jsonify({
                'success': False,
                'message': f'数据库文件不存在: {database_file}'
            }), 400

        logger.info(f"数据库文件存在: {file_path}")

        # 准备multipart/form-data请求
        with open(file_path, 'rb') as f:
            # 只发送文件名，不发送完整路径，避免Windows路径转义问题
            filename_only = os.path.basename(database_file)
            files = {
                'database_file': (filename_only, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data_form = {
                'entity': entity
            }

            logger.info(f"准备调用后端API: {BACKEND_URL}/finance/visualization/generate-visualization")
            logger.info(f"请求参数: {data_form}")

            # 调用FastAPI后端
            backend_response = requests.post(
                f'{BACKEND_URL}/finance/visualization/generate-visualization',
                files=files,
                data=data_form,
                timeout=900  # Increased from 300 to 900 seconds (15 minutes)
            )

        logger.info(f"后端响应状态码: {backend_response.status_code}")
        logger.info(f"后端响应内容类型: {backend_response.headers.get('content-type')}")

        if backend_response.status_code == 200:
            # 检查响应内容类型
            content_type = backend_response.headers.get('content-type', '')
            logger.info(f"响应内容类型: {content_type}")
            logger.info(f"响应内容长度: {len(backend_response.content)}")
            logger.info(f"响应头: {dict(backend_response.headers)}")

            # 首先尝试解析为JSON（后端通常返回JSON结果）
            try:
                result = backend_response.json()
                logger.info(f"JSON响应解析成功: {result}")

                # 查找文件路径信息
                file_path_in_response = None
                possible_keys = ['file_path', 'output_file', 'visualization_file', 'result_file']

                for key in possible_keys:
                    if key in result and result[key]:
                        file_path_in_response = result[key]
                        logger.info(f"从JSON响应中找到文件路径 ({key}): {file_path_in_response}")
                        break

                # 如果JSON中没有直接的文件路径，检查是否有嵌套结构
                if not file_path_in_response and 'message' in result:
                    message = result['message']
                    # 从日志消息中提取文件路径
                    if '已成功保存可视化文件:' in message:
                        import re
                        # 匹配文件路径模式
                        path_match = re.search(r'已成功保存可视化文件:\s*([^\s,，]+)', message)
                        if path_match:
                            file_path_in_response = path_match.group(1).strip()
                            logger.info(f"从消息中提取的文件路径: {file_path_in_response}")

                # 如果找到了文件路径，尝试复制文件
                if file_path_in_response:
                    logger.info(f"准备处理文件: {file_path_in_response}")

                    # 检查文件是否存在
                    if os.path.exists(file_path_in_response):
                        logger.info(f"找到生成的文件: {file_path_in_response}")

                        # 确定目标文件名和扩展名
                        original_filename = os.path.basename(file_path_in_response)
                        file_extension = os.path.splitext(original_filename)[1].lower()

                        # 根据文件扩展名确定文件类型
                        if file_extension == '.xlsx':
                            filename = f"Visualization_{entity}_{financial_year}.xlsx"
                            file_type = 'xlsx'
                        elif file_extension == '.docx':
                            filename = f"Visualization_{entity}_{financial_year}.docx"
                            file_type = 'docx'
                        elif file_extension == '.zip':
                            filename = f"Visualization_{entity}_{financial_year}.zip"
                            file_type = 'zip'
                        else:
                            # 保持原始扩展名
                            filename = f"Visualization_{entity}_{financial_year}{file_extension}"
                            file_type = file_extension[1:] if file_extension else 'unknown'

                        logger.info(f"目标文件名: {filename}, 文件类型: {file_type}")

                        # 确保下载目录存在
                        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
                        downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                        try:
                            # 复制文件
                            import shutil
                            shutil.copy2(file_path_in_response, downloads_path)
                            logger.info(f"文件已从 {file_path_in_response} 复制到 {downloads_path}")

                            # 验证复制的文件
                            if os.path.exists(downloads_path):
                                file_size = os.path.getsize(downloads_path)
                                logger.info(f"复制的文件大小: {file_size} 字节")

                                if file_size > 0:
                                    return jsonify({
                                        'success': True,
                                        'message': '可视化生成成功！',
                                        'download_url': url_for('download_file', filename=filename),
                                        'file_type': file_type,
                                        'original_path': file_path_in_response
                                    })
                                else:
                                    logger.error("复制的文件大小为0")
                                    return jsonify({
                                        'success': False,
                                        'message': '生成的文件为空'
                                    }), 500
                            else:
                                logger.error("文件复制失败，目标文件不存在")
                                return jsonify({
                                    'success': False,
                                    'message': '文件复制失败'
                                }), 500
                        except Exception as e:
                            logger.error(f"复制文件失败: {str(e)}")
                            return jsonify({
                                'success': False,
                                'message': f'复制文件失败: {str(e)}'
                            }), 500
                    else:
                        logger.error(f"指定的文件路径不存在: {file_path_in_response}")

                        # 尝试在预期的目录中查找文件
                        expected_dirs = [
                            settings.PROCESSED_DATA_DIR + '/visualization',
                            os.path.join(settings.PROCESSED_DATA_DIR, 'visualization'),
                            app.config['DOWNLOADS_FOLDER']
                        ]

                        found_file = None
                        for search_dir in expected_dirs:
                            if os.path.exists(search_dir):
                                logger.info(f"搜索目录: {search_dir}")
                                for filename in os.listdir(search_dir):
                                    if entity in filename and filename.endswith(('.docx', '.xlsx', '.zip')):
                                        found_file = os.path.join(search_dir, filename)
                                        logger.info(f"找到匹配文件: {found_file}")
                                        break
                                if found_file:
                                    # 找到文件后跳出外层循环
                                    break
                        if found_file:
                            # 找到文件后不再继续搜索其他目录
                            logger.info(f"已找到文件，停止搜索其他目录")

                        # 处理找到的文件
                        if found_file and os.path.exists(found_file):
                            logger.info(f"使用搜索到的文件: {found_file}")
                            # 处理找到的文件（类似上面的逻辑）
                            original_filename = os.path.basename(found_file)
                            file_extension = os.path.splitext(original_filename)[1].lower()

                            if file_extension == '.xlsx':
                                filename = f"Visualization_{entity}_{financial_year}.xlsx"
                                file_type = 'xlsx'
                            elif file_extension == '.docx':
                                filename = f"Visualization_{entity}_{financial_year}.docx"
                                file_type = 'docx'
                            elif file_extension == '.zip':
                                filename = f"Visualization_{entity}_{financial_year}.zip"
                                file_type = 'zip'
                            else:
                                filename = f"Visualization_{entity}_{financial_year}{file_extension}"
                                file_type = file_extension[1:] if file_extension else 'unknown'

                            downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                            try:
                                import shutil
                                shutil.copy2(found_file, downloads_path)
                                logger.info(f"文件已从 {found_file} 复制到 {downloads_path}")

                                return jsonify({
                                    'success': True,
                                    'message': '可视化生成成功！',
                                    'download_url': url_for('download_file', filename=filename),
                                    'file_type': file_type,
                                    'original_path': found_file
                                })
                            except Exception as e:
                                logger.error(f"复制搜索到的文件失败: {str(e)}")
                        else:
                            logger.error("在预期目录中未找到生成的文件")

                # 如果没有找到文件路径，返回JSON结果
                return jsonify({
                    'success': True,
                    'message': '可视化处理完成',
                    'result': result
                })

            except ValueError as json_error:
                logger.warning(f"响应不是JSON格式: {str(json_error)}")
                # 如果不是JSON，按原来的逻辑处理为文件内容
                pass

            # 保存原始响应内容到调试文件
            debug_file = os.path.join(app.config['DOWNLOADS_FOLDER'], f"debug_response_{entity}_{financial_year}.raw")
            os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
            try:
                with open(debug_file, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"原始响应已保存到调试文件: {debug_file}")
            except Exception as e:
                logger.error(f"保存调试文件失败: {str(e)}")

            # 检查响应内容是否为空
            if len(backend_response.content) == 0:
                logger.error("后端返回空内容")
                return jsonify({
                    'success': False,
                    'message': '后端返回空文件'
                }), 500

            # 作为二进制文件处理（当响应不是JSON时）
            logger.info("将响应作为二进制文件处理")

            # 根据文件头判断文件类型
            file_header = backend_response.content[:8] if len(
                backend_response.content) >= 8 else backend_response.content
            logger.info(f"文件头部信息: {file_header}")

            filename = None
            file_type = None
            if file_header.startswith(b'PK\x03\x04'):
                # ZIP文件头（Excel和Word文档都是ZIP格式）
                if b'xl/' in backend_response.content or b'[Content_Types].xml' in backend_response.content:
                    # 检查是否包含Excel特有的内容
                    if b'xl/workbook.xml' in backend_response.content:
                        filename = f"Visualization_{entity}_{financial_year}.xlsx"
                        file_type = 'xlsx'
                        logger.info("检测到Excel文件格式")
                    elif b'word/' in backend_response.content or b'document.xml' in backend_response.content:
                        filename = f"Visualization_{entity}_{financial_year}.docx"
                        file_type = 'docx'
                        logger.info("检测到Word文档格式")
                    else:
                        # 可视化默认为docx文件
                        filename = f"Visualization_{entity}_{financial_year}.docx"
                        file_type = 'docx'
                        logger.info("检测到Office文档格式，默认为Word文档")
                else:
                    filename = f"Visualization_{entity}_{financial_year}.zip"
                    file_type = 'zip'
                    logger.info("检测到ZIP文件格式")
            elif file_header.startswith(b'\xd0\xcf\x11\xe0'):
                filename = f"Visualization_{entity}_{financial_year}.xls"
                file_type = 'xls'
                logger.info("检测到旧版Excel文件格式")
            elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                filename = f"Visualization_{entity}_{financial_year}.docx"
                file_type = 'docx'
                logger.info("根据Content-Type检测到Word文档")
            elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                filename = f"Visualization_{entity}_{financial_year}.xlsx"
                file_type = 'xlsx'
                logger.info("根据Content-Type检测到Excel文件")
            elif 'application/zip' in content_type:
                filename = f"Visualization_{entity}_{financial_year}.zip"
                file_type = 'zip'
                logger.info("根据Content-Type检测到ZIP文件")
            else:
                # 可视化默认为docx文件
                filename = f"Visualization_{entity}_{financial_year}.docx"
                file_type = 'docx'
                logger.warning(f"无法识别文件类型，默认保存为Word文档: {filename}")

            # 保存文件
            file_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
            try:
                with open(file_path, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"文件已保存到: {file_path}")

                # 验证文件大小
                file_size = os.path.getsize(file_path)
                logger.info(f"保存的文件大小: {file_size} 字节")

                if file_size == 0:
                    logger.error("保存的文件大小为0")
                    return jsonify({
                        'success': False,
                        'message': '生成的文件为空'
                    }), 500

                return jsonify({
                    'success': True,
                    'message': '可视化文件已生成！',
                    'download_url': url_for('download_file', filename=filename),
                    'file_type': file_type
                })

            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'保存文件失败: {str(e)}'
                }), 500
        else:
            logger.error(f"后端处理失败: {backend_response.status_code}, {backend_response.text}")
            return jsonify({
                'success': False,
                'message': f'后端处理失败: {backend_response.text}'
            }), 500

    except requests.Timeout:
        logger.error("Request timeout")
        return jsonify({
            'success': False,
            'message': 'Processing timeout, please try again later'
        }), 500
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Processing failed: {str(e)}'
        }), 500


@app.route('/api/generate_reporting', methods=['POST'])
def api_generate_reporting():
    """调用后端API生成报告"""
    try:
        logger.info("=== 开始处理reporting请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")

        # 同时支持表单数据和JSON数据
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = {
                'database_file': request.form.get('database_file'),
                'entity': request.form.get('entity'),
                'financial_year': request.form.get('financial_year')
            }
            logger.info(f"表单数据: {data}")

        database_file = data.get('database_file')
        entity = data.get('entity')
        financial_year = data.get('financial_year')

        logger.info(f"解析后的参数: database_file={database_file}, entity={entity}, financial_year={financial_year}")

        if not database_file:
            logger.error("未提供数据库文件")
            return jsonify({
                'success': False,
                'message': 'Please provide database file'
            }), 400

        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], database_file)
        if not os.path.exists(file_path):
            logger.error(f"数据库文件不存在: {file_path}")
            return jsonify({
                'success': False,
                'message': f'数据库文件不存在: {database_file}'
            }), 400

        logger.info(f"数据库文件存在: {file_path}")

        # 准备multipart/form-data请求
        with open(file_path, 'rb') as f:
            # 只发送文件名，不发送完整路径，避免Windows路径转义问题
            filename_only = os.path.basename(database_file)
            files = {
                'database_file': (filename_only, f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data_form = {
                'entity': entity
            }

            logger.info(f"准备调用后端API: {BACKEND_URL}/finance/reporting/generate-report")
            logger.info(f"请求参数: {data_form}")

            # 调用FastAPI后端
            backend_response = requests.post(
                f'{BACKEND_URL}/finance/reporting/generate-report',
                files=files,
                data=data_form,
                timeout=900  # Increased from 300 to 900 seconds (15 minutes)
            )

        logger.info(f"后端响应状态码: {backend_response.status_code}")
        logger.info(f"后端响应内容类型: {backend_response.headers.get('content-type')}")

        if backend_response.status_code == 200:
            # 检查响应内容类型
            content_type = backend_response.headers.get('content-type', '')
            logger.info(f"响应内容类型: {content_type}")
            logger.info(f"响应内容长度: {len(backend_response.content)}")
            logger.info(f"响应头: {dict(backend_response.headers)}")

            # 首先尝试解析为JSON（后端通常返回JSON结果）
            try:
                result = backend_response.json()
                logger.info(f"JSON响应解析成功: {result}")

                # 查找文件路径信息
                file_path_in_response = None
                possible_keys = ['file_path', 'output_file', 'report_file', 'result_file']

                for key in possible_keys:
                    if key in result and result[key]:
                        file_path_in_response = result[key]
                        logger.info(f"从JSON响应中找到文件路径 ({key}): {file_path_in_response}")
                        break

                # 如果JSON中没有直接的文件路径，检查是否有嵌套结构
                if not file_path_in_response and 'message' in result:
                    message = result['message']
                    # 从日志消息中提取文件路径
                    if '已成功保存报告文件:' in message:
                        import re
                        # 匹配文件路径模式
                        path_match = re.search(r'已成功保存报告文件:\s*([^\s,，]+)', message)
                        if path_match:
                            file_path_in_response = path_match.group(1).strip()
                            logger.info(f"从消息中提取的文件路径: {file_path_in_response}")

                # 如果找到了文件路径，尝试复制文件
                if file_path_in_response:
                    logger.info(f"准备处理文件: {file_path_in_response}")

                    # 检查文件是否存在
                    if os.path.exists(file_path_in_response):
                        logger.info(f"找到生成的文件: {file_path_in_response}")

                        # 确定目标文件名和扩展名
                        original_filename = os.path.basename(file_path_in_response)
                        file_extension = os.path.splitext(original_filename)[1].lower()

                        # 根据文件扩展名确定文件类型
                        if file_extension == '.docx':
                            filename = f"Report_{entity}_{financial_year}.docx"
                            file_type = 'docx'
                        elif file_extension == '.xlsx':
                            filename = f"Report_{entity}_{financial_year}.xlsx"
                            file_type = 'xlsx'
                        elif file_extension == '.zip':
                            filename = f"Report_{entity}_{financial_year}.zip"
                            file_type = 'zip'
                        else:
                            # 报告默认为docx文件
                            filename = f"Report_{entity}_{financial_year}.docx"
                            file_type = 'docx'

                        logger.info(f"目标文件名: {filename}, 文件类型: {file_type}")

                        # 确保下载目录存在
                        os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
                        downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                        try:
                            # 复制文件
                            shutil.copy2(file_path_in_response, downloads_path)
                            logger.info(f"文件已从 {file_path_in_response} 复制到 {downloads_path}")

                            # 验证复制的文件
                            if os.path.exists(downloads_path):
                                file_size = os.path.getsize(downloads_path)
                                logger.info(f"复制的文件大小: {file_size} 字节")

                                if file_size > 0:
                                    return jsonify({
                                        'success': True,
                                        'message': '报告生成成功！',
                                        'download_url': url_for('download_file', filename=filename),
                                        'file_type': file_type,
                                        'original_path': file_path_in_response
                                    })
                                else:
                                    logger.error("复制的文件大小为0")
                                    return jsonify({
                                        'success': False,
                                        'message': '生成的文件为空'
                                    }), 500
                            else:
                                logger.error("文件复制失败，目标文件不存在")
                                return jsonify({
                                    'success': False,
                                    'message': '文件复制失败'
                                }), 500
                        except Exception as e:
                            logger.error(f"复制文件失败: {str(e)}")
                            return jsonify({
                                'success': False,
                                'message': f'复制文件失败: {str(e)}'
                            }), 500
                    else:
                        logger.error(f"指定的文件路径不存在: {file_path_in_response}")

                        # 尝试在预期的目录中查找文件
                        expected_dirs = [
                            settings.PROCESSED_DATA_DIR + '/reporting',
                            os.path.join(settings.PROCESSED_DATA_DIR, 'reporting'),
                            app.config['DOWNLOADS_FOLDER']
                        ]

                        found_file = None
                        for search_dir in expected_dirs:
                            if os.path.exists(search_dir):
                                logger.info(f"搜索目录: {search_dir}")
                                for filename in os.listdir(search_dir):
                                    if entity in filename and filename.endswith(('.docx', '.xlsx', '.zip')):
                                        found_file = os.path.join(search_dir, filename)
                                        logger.info(f"找到匹配文件: {found_file}")
                                        break
                                if found_file:
                                    break

                        # 处理找到的文件
                        if found_file and os.path.exists(found_file):
                            logger.info(f"使用搜索到的文件: {found_file}")
                            original_filename = os.path.basename(found_file)
                            file_extension = os.path.splitext(original_filename)[1].lower()

                            if file_extension == '.docx':
                                filename = f"Report_{entity}_{financial_year}.docx"
                                file_type = 'docx'
                            elif file_extension == '.xlsx':
                                filename = f"Report_{entity}_{financial_year}.xlsx"
                                file_type = 'xlsx'
                            elif file_extension == '.zip':
                                filename = f"Report_{entity}_{financial_year}.zip"
                                file_type = 'zip'
                            else:
                                filename = f"Report_{entity}_{financial_year}{file_extension}"
                                file_type = file_extension[1:] if file_extension else 'unknown'

                            downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                            try:
                                shutil.copy2(found_file, downloads_path)
                                logger.info(f"文件已从 {found_file} 复制到 {downloads_path}")

                                return jsonify({
                                    'success': True,
                                    'message': '报告生成成功！',
                                    'download_url': url_for('download_file', filename=filename),
                                    'file_type': file_type,
                                    'original_path': found_file
                                })
                            except Exception as e:
                                logger.error(f"复制搜索到的文件失败: {str(e)}")
                        else:
                            logger.error("在预期目录中未找到生成的文件")

                # 如果没有找到文件路径，返回JSON结果
                return jsonify({
                    'success': True,
                    'message': '报告处理完成',
                    'result': result
                })

            except ValueError as json_error:
                logger.warning(f"响应不是JSON格式: {str(json_error)}")
                # 如果不是JSON，按原来的逻辑处理为文件内容
                pass

            # 保存原始响应内容到调试文件
            debug_file = os.path.join(app.config['DOWNLOADS_FOLDER'],
                                      f"debug_response_report_{entity}_{financial_year}.raw")
            os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
            try:
                with open(debug_file, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"原始响应已保存到调试文件: {debug_file}")
            except Exception as e:
                logger.error(f"保存调试文件失败: {str(e)}")

            # 检查响应内容是否为空
            if len(backend_response.content) == 0:
                logger.error("后端返回空内容")
                return jsonify({
                    'success': False,
                    'message': '后端返回空文件'
                }), 500

            # 作为二进制文件处理（当响应不是JSON时）
            logger.info("将响应作为二进制文件处理")

            # 根据文件头判断文件类型
            file_header = backend_response.content[:8] if len(
                backend_response.content) >= 8 else backend_response.content
            logger.info(f"文件头部信息: {file_header}")

            filename = None
            file_type = None
            if file_header.startswith(b'PK\x03\x04'):
                # ZIP文件头（Word文档是ZIP格式）
                if b'word/' in backend_response.content or b'document.xml' in backend_response.content:
                    filename = f"Report_{entity}_{financial_year}.docx"
                    file_type = 'docx'
                    logger.info("检测到Word文档格式")
                elif b'xl/workbook.xml' in backend_response.content:
                    filename = f"Report_{entity}_{financial_year}.xlsx"
                    file_type = 'xlsx'
                    logger.info("检测到Excel文件格式")
                else:
                    # 报告默认为docx文件
                    filename = f"Report_{entity}_{financial_year}.docx"
                    file_type = 'docx'
                    logger.info("检测到Office文档格式，默认为Word文档")
            elif file_header.startswith(b'\xd0\xcf\x11\xe0'):
                filename = f"Report_{entity}_{financial_year}.doc"
                file_type = 'doc'
                logger.info("检测到旧版Word文档格式")
            elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                filename = f"Report_{entity}_{financial_year}.docx"
                file_type = 'docx'
                logger.info("根据Content-Type检测到Word文档")
            elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                filename = f"Report_{entity}_{financial_year}.xlsx"
                file_type = 'xlsx'
                logger.info("根据Content-Type检测到Excel文件")
            elif 'application/zip' in content_type:
                filename = f"Report_{entity}_{financial_year}.zip"
                file_type = 'zip'
                logger.info("根据Content-Type检测到ZIP文件")
            else:
                # 报告默认为docx文件
                filename = f"Report_{entity}_{financial_year}.docx"
                file_type = 'docx'
                logger.warning(f"无法识别文件类型，默认保存为Word文档: {filename}")

            # 保存文件
            file_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
            try:
                with open(file_path, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"文件已保存到: {file_path}")

                # 验证文件大小
                file_size = os.path.getsize(file_path)
                logger.info(f"保存的文件大小: {file_size} 字节")

                if file_size == 0:
                    logger.error("保存的文件大小为0")
                    return jsonify({
                        'success': False,
                        'message': '生成的文件为空'
                    }), 500

                return jsonify({
                    'success': True,
                    'message': '报告文件已生成！',
                    'download_url': url_for('download_file', filename=filename),
                    'file_type': file_type
                })

            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'保存文件失败: {str(e)}'
                }), 500
        else:
            logger.error(f"后端处理失败: {backend_response.status_code}, {backend_response.text}")
            return jsonify({
                'success': False,
                'message': f'后端处理失败: {backend_response.text}'
            }), 500

    except requests.Timeout:
        logger.error("Request timeout")
        return jsonify({
            'success': False,
            'message': 'Processing timeout, please try again later'
        }), 500
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Processing failed: {str(e)}'
        }), 500


@app.route('/api/execute_workflow', methods=['POST'])
def api_execute_workflow():
    """调用后端API执行工作流"""
    try:
        logger.info("=== 开始处理workflow请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")
        logger.info(f"Request is_json: {request.is_json}")
        logger.info(f"Request form: {dict(request.form)}")
        logger.info(f"Request files: {list(request.files.keys())}")

        # 同时支持表单数据和JSON数据
        if request.is_json:
            data = request.get_json()
            logger.info(f"JSON数据: {data}")
        else:
            data = {
                'pl_file': request.form.get('pl_file'),
                'bs_file': request.form.get('bs_file'),
                'entity': request.form.get('entity'),
                'financial_year': request.form.get('financial_year')
            }
            logger.info(f"表单数据: {data}")

        pl_file = data.get('pl_file')
        bs_file = data.get('bs_file')
        entity = data.get('entity')
        financial_year = data.get('financial_year')

        logger.info(
            f"解析后的参数: pl_file={pl_file}, bs_file={bs_file}, entity={entity}, financial_year={financial_year}")

        # 验证必要参数
        if not pl_file or not bs_file:
            logger.error(f"文件名验证失败: pl_file={pl_file}, bs_file={bs_file}")
            return jsonify({
                'success': False,
                'message': '请提供PL文件和BS文件名'
            }), 400

        if not entity or not financial_year:
            logger.error(f"实体信息验证失败: entity={entity}, financial_year={financial_year}")
            return jsonify({
                'success': False,
                'message': '请提供实体名称和财务年度'
            }), 400

        # 确保上传目录存在
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        # 构建文件路径
        pl_path = os.path.join(app.config['UPLOAD_FOLDER'], pl_file)
        bs_path = os.path.join(app.config['UPLOAD_FOLDER'], bs_file)

        # 检查文件是否存在
        if not os.path.exists(pl_path):
            logger.error(f"PL文件不存在: {pl_path}")
            return jsonify({
                'success': False,
                'message': f'PL file not found: {pl_file}'
            }), 400

        if not os.path.exists(bs_path):
            logger.error(f"BS文件不存在: {bs_path}")
            return jsonify({
                'success': False,
                'message': f'BS file not found: {bs_file}'
            }), 400

        logger.info(f"文件存在验证通过: PL={pl_path}, BS={bs_path}")

        # 准备multipart/form-data请求
        with open(pl_path, 'rb') as pl_f, open(bs_path, 'rb') as bs_f:
            files = {
                'pl_file': (pl_file, pl_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
                'bs_file': (bs_file, bs_f, 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
            }
            data_form = {
                'entity': entity
            }

            logger.info(f"准备调用后端API: {BACKEND_URL}/finance/workflow/execute-workflow")
            logger.info(f"请求参数: {data_form}")

            # 调用FastAPI后端
            backend_response = requests.post(
                f'{BACKEND_URL}/finance/workflow/execute-workflow',
                files=files,
                data=data_form,
                timeout=1200  # Increased from 600 to 1200 seconds (20 minutes for full workflow)
            )

        logger.info(f"后端响应状态码: {backend_response.status_code}")
        logger.info(f"后端响应内容类型: {backend_response.headers.get('content-type')}")

        if backend_response.status_code == 200:
            # 检查响应内容类型
            content_type = backend_response.headers.get('content-type', '')
            logger.info(f"响应内容类型: {content_type}")
            logger.info(f"响应内容长度: {len(backend_response.content)}")

            # 首先尝试解析为JSON
            try:
                result = backend_response.json()
                logger.info(f"JSON响应解析成功: {result}")

                # 工作流可能返回任务ID或直接结果
                if 'task_id' in result:
                    logger.info(f"工作流返回任务ID: {result['task_id']}")
                    return jsonify({
                        'success': True,
                        'message': '工作流已启动！',
                        'task_id': result['task_id'],
                        'result': result
                    })

                # 查找文件路径信息（如果工作流直接返回文件）
                file_paths = []
                possible_keys = ['files', 'output_files', 'result_files', 'workflow_files']

                for key in possible_keys:
                    if key in result and result[key]:
                        if isinstance(result[key], list):
                            file_paths.extend(result[key])
                        else:
                            file_paths.append(result[key])
                        logger.info(f"从JSON响应中找到文件路径 ({key}): {result[key]}")

                # 如果找到了文件路径，尝试复制文件
                if file_paths:
                    logger.info(f"准备处理工作流文件: {file_paths}")
                    download_urls = []

                    for i, file_path in enumerate(file_paths):
                        if os.path.exists(file_path):
                            logger.info(f"找到生成的文件 {i + 1}: {file_path}")

                            # 根据文件类型确定文件名
                            original_filename = os.path.basename(file_path)
                            file_extension = os.path.splitext(original_filename)[1].lower()

                            if 'summary' in original_filename.lower():
                                filename = f"Workflow_Summary_{entity}_{financial_year}{file_extension}"
                            elif 'database' in original_filename.lower():
                                filename = f"Workflow_Database_{entity}_{financial_year}{file_extension}"
                            elif 'visualization' in original_filename.lower():
                                filename = f"Workflow_Visualization_{entity}_{financial_year}{file_extension}"
                            elif 'report' in original_filename.lower():
                                filename = f"Workflow_Report_{entity}_{financial_year}{file_extension}"
                            else:
                                filename = f"Workflow_{entity}_{financial_year}_{i + 1}{file_extension}"

                            os.makedirs(app.config['DOWNLOADS_FOLDER'], exist_ok=True)
                            downloads_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)

                            try:
                                shutil.copy2(file_path, downloads_path)
                                logger.info(f"文件已从 {file_path} 复制到 {downloads_path}")

                                if os.path.exists(downloads_path) and os.path.getsize(downloads_path) > 0:
                                    download_urls.append({
                                        'filename': filename,
                                        'download_url': url_for('download_file', filename=filename),
                                        'file_type': file_extension[1:] if file_extension else 'unknown'
                                    })
                                else:
                                    logger.error(f"复制的文件为空或不存在: {filename}")
                            except Exception as e:
                                logger.error(f"复制文件失败 {file_path}: {str(e)}")
                        else:
                            logger.warning(f"文件不存在: {file_path}")

                    if download_urls:
                        return jsonify({
                            'success': True,
                            'message': '工作流执行成功！',
                            'download_urls': download_urls,
                            'result': result
                        })

                # 如果没有找到文件路径，返回JSON结果
                return jsonify({
                    'success': True,
                    'message': '工作流执行完成！',
                    'result': result
                })

            except ValueError as json_error:
                logger.warning(f"响应不是JSON格式: {str(json_error)}")
                pass

            # 检查响应内容是否为空
            if len(backend_response.content) == 0:
                logger.error("后端返回空内容")
                return jsonify({
                    'success': False,
                    'message': '后端返回空内容'
                }), 500

            # 作为二进制文件处理（如果工作流直接返回单个文件）
            logger.info("将响应作为二进制文件处理")

            # 根据文件头判断文件类型
            file_header = backend_response.content[:8] if len(
                backend_response.content) >= 8 else backend_response.content
            logger.info(f"文件头部信息: {file_header}")

            # 工作流可能返回各种类型的文件
            filename = None
            file_type = None

            if file_header.startswith(b'PK\x03\x04'):
                # ZIP文件头（Word文档是ZIP格式）
                if b'word/' in backend_response.content or b'document.xml' in backend_response.content:
                    filename = f"Workflow_{entity}_{financial_year}.docx"
                    file_type = 'docx'
                    logger.info("检测到Word文档格式")
                elif b'xl/workbook.xml' in backend_response.content:
                    filename = f"Workflow_{entity}_{financial_year}.xlsx"
                    file_type = 'xlsx'
                    logger.info("检测到Excel文件格式")
                else:
                    # 工作流默认为ZIP文件（可能包含多个文件）
                    filename = f"Workflow_{entity}_{financial_year}.zip"
                    file_type = 'zip'
                    logger.info("使用默认ZIP格式")
            elif file_header.startswith(b'\xd0\xcf\x11\xe0'):
                filename = f"Workflow_{entity}_{financial_year}.doc"
                file_type = 'doc'
                logger.info("检测到旧版Word文档格式")
            elif 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' in content_type:
                filename = f"Workflow_{entity}_{financial_year}.docx"
                file_type = 'docx'
                logger.info("根据Content-Type检测到Word文档")
            elif 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' in content_type:
                filename = f"Workflow_{entity}_{financial_year}.xlsx"
                file_type = 'xlsx'
                logger.info("根据Content-Type检测到Excel文件")
            elif 'application/zip' in content_type:
                filename = f"Workflow_{entity}_{financial_year}.zip"
                file_type = 'zip'
                logger.info("根据Content-Type检测到ZIP文件")
            else:
                # 工作流默认为ZIP文件（可能包含多个文件）
                filename = f"Workflow_{entity}_{financial_year}.zip"
                file_type = 'zip'
                logger.info("使用默认ZIP格式")

            # 保存文件
            file_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
            try:
                with open(file_path, 'wb') as f:
                    f.write(backend_response.content)
                logger.info(f"文件已保存到: {file_path}")

                # 验证文件大小
                file_size = os.path.getsize(file_path)
                logger.info(f"保存的文件大小: {file_size} 字节")

                if file_size == 0:
                    logger.error("保存的文件大小为0")
                    return jsonify({
                        'success': False,
                        'message': '生成的文件为空'
                    }), 500

                return jsonify({
                    'success': True,
                    'message': '工作流执行成功！',
                    'download_url': url_for('download_file', filename=filename),
                    'file_type': file_type
                })

            except Exception as e:
                logger.error(f"保存文件失败: {str(e)}")
                return jsonify({
                    'success': False,
                    'message': f'保存文件失败: {str(e)}'
                }), 500
        else:
            logger.error(f"后端处理失败: {backend_response.status_code}, {backend_response.text}")
            return jsonify({
                'success': False,
                'message': f'后端处理失败: {backend_response.text}'
            }), 500

    except requests.Timeout:
        logger.error("Request timeout")
        return jsonify({
            'success': False,
            'message': 'Processing timeout, please try again later'
        }), 500
    except Exception as e:
        logger.error(f"API调用失败: {str(e)}")
        return jsonify({
            'success': False,
            'message': f'Processing failed: {str(e)}'
        }), 500


@app.route('/api/workflow_status/<task_id>')
def api_workflow_status(task_id):
    """查询工作流状态"""
    try:
        logger.info(f"=== 查询工作流状态: {task_id} ===")

        # 参数验证
        if not task_id or not task_id.strip():
            logger.error("任务ID为空")
            return jsonify({
                'success': False,
                'message': '任务ID不能为空'
            }), 400

        logger.info(f"准备查询工作流状态: {BACKEND_URL}/finance/workflow/workflow-status/{task_id}")

        backend_response = requests.get(
            f'{BACKEND_URL}/finance/workflow/workflow-status/{task_id}',
            timeout=30
        )

        logger.info(f"后端响应状态码: {backend_response.status_code}")

        if backend_response.status_code == 200:
            result = backend_response.json()
            logger.info(f"工作流状态查询成功: {result.get('status', '未知状态')}")
            return jsonify(result)
        else:
            logger.error(f"工作流状态查询失败: {backend_response.status_code}, {backend_response.text}")
            return jsonify({
                'success': False,
                'message': f'查询失败: {backend_response.text}'
            }), backend_response.status_code

    except requests.Timeout:
        logger.error(f"查询工作流状态超时: {task_id}")
        return jsonify({
            'success': False,
            'message': '查询超时，请稍后重试'
        }), 500
    except Exception as e:
        logger.error(f"获取工作流状态失败: {str(e)}")
        return jsonify({
            'success': False,
            'status': 'error',
            'message': f'查询失败: {str(e)}'
        }), 500


@app.route('/api/list_files', methods=['GET'])
def list_files():
    """列出已上传和生成的文件"""
    try:
        logger.info("=== 开始列出文件 ===")

        # 列出上传文件
        uploads_dir = app.config['UPLOAD_FOLDER']
        uploaded_files = []
        logger.info(f"检查上传目录: {uploads_dir}")

        if os.path.exists(uploads_dir):
            all_upload_files = os.listdir(uploads_dir)
            uploaded_files = [f for f in all_upload_files if f.endswith(('.xlsx', '.xls'))]
            logger.info(f"找到 {len(uploaded_files)} 个上传文件: {uploaded_files}")
        else:
            logger.warning(f"上传目录不存在: {uploads_dir}")

        # 列出下载文件
        downloads_dir = app.config['DOWNLOADS_FOLDER']
        download_files = []
        logger.info(f"检查下载目录: {downloads_dir}")

        if os.path.exists(downloads_dir):
            all_download_files = os.listdir(downloads_dir)
            download_files = [f for f in all_download_files if f.endswith(('.xlsx', '.docx', '.zip', '.xls'))]
            logger.info(f"找到 {len(download_files)} 个下载文件: {download_files}")
        else:
            logger.warning(f"下载目录不存在: {downloads_dir}")

        # 获取文件详细信息
        uploaded_files_info = []
        for filename in uploaded_files:
            file_path = os.path.join(uploads_dir, filename)
            try:
                file_stat = os.stat(file_path)
                uploaded_files_info.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'modified_time': file_stat.st_mtime
                })
            except Exception as e:
                logger.warning(f"获取上传文件信息失败 {filename}: {str(e)}")
                uploaded_files_info.append({
                    'filename': filename,
                    'size': 0,
                    'modified_time': 0
                })

        download_files_info = []
        for filename in download_files:
            file_path = os.path.join(downloads_dir, filename)
            try:
                file_stat = os.stat(file_path)
                download_files_info.append({
                    'filename': filename,
                    'size': file_stat.st_size,
                    'modified_time': file_stat.st_mtime
                })
            except Exception as e:
                logger.warning(f"获取下载文件信息失败 {filename}: {str(e)}")
                download_files_info.append({
                    'filename': filename,
                    'size': 0,
                    'modified_time': 0
                })

        result = {
            'success': True,
            'uploaded_files': uploaded_files,
            'download_files': download_files,
            'uploaded_files_info': uploaded_files_info,
            'download_files_info': download_files_info,
            'upload_count': len(uploaded_files),
            'download_count': len(download_files)
        }

        logger.info(f"文件列表查询成功: 上传文件 {len(uploaded_files)} 个，下载文件 {len(download_files)} 个")
        return jsonify(result)

    except Exception as e:
        logger.error(f"列出文件失败: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'列出文件失败: {str(e)}'
        }), 500


@app.route('/api/delete_file', methods=['POST'])
def delete_file():
    """删除文件"""
    try:
        logger.info("=== 开始处理删除文件请求 ===")
        logger.info(f"Request method: {request.method}")
        logger.info(f"Request content type: {request.content_type}")

        data = request.get_json()
        logger.info(f"请求数据: {data}")

        if not data:
            logger.error("请求数据为空")
            return jsonify({'error': '请求数据为空'}), 400

        filename = data.get('filename')
        file_type = data.get('type')  # 'upload' or 'download'

        logger.info(f"删除文件参数: filename={filename}, type={file_type}")

        # 参数验证
        if not filename:
            logger.error("文件名为空")
            return jsonify({'error': '文件名不能为空'}), 400

        if not file_type:
            logger.error("文件类型为空")
            return jsonify({'error': '文件类型不能为空'}), 400

        # 安全检查：防止路径遍历攻击
        if '..' in filename or '/' in filename or '\\' in filename:
            logger.error(f"不安全的文件名: {filename}")
            return jsonify({'error': '不安全的文件名'}), 400

        if file_type == 'upload':
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            logger.info(f"准备删除上传文件: {file_path}")
        elif file_type == 'download':
            file_path = os.path.join(app.config['DOWNLOADS_FOLDER'], filename)
            logger.info(f"准备删除下载文件: {file_path}")
        else:
            logger.error(f"无效的文件类型: {file_type}")
            return jsonify({'error': '无效的文件类型，只支持 upload 或 download'}), 400

        if os.path.exists(file_path):
            # 记录文件信息
            file_size = os.path.getsize(file_path)
            logger.info(f"文件存在，大小: {file_size} 字节")

            os.remove(file_path)
            logger.info(f"文件删除成功: {file_path}")

            return jsonify({
                'success': True,
                'message': '文件删除成功',
                'filename': filename,
                'file_type': file_type
            })
        else:
            logger.warning(f"文件不存在: {file_path}")
            return jsonify({'error': '文件不存在'}), 404

    except Exception as e:
        logger.error(f"删除文件失败: {str(e)}")
        return jsonify({'error': f'删除文件失败: {str(e)}'}), 500


@app.errorhandler(404)
def not_found_error(error):
    """404错误处理"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def internal_error(error):
    """500错误处理"""
    return render_template('500.html'), 500


if __name__ == '__main__':
    # 运行应用
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
