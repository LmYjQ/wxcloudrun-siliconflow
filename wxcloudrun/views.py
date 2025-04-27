from datetime import datetime
from flask import render_template, request, Response, stream_with_context
import os
import requests
from run import app
from wxcloudrun.dao import delete_counterbyid, query_counterbyid, insert_counter, update_counterbyid
from wxcloudrun.model import Counters
from wxcloudrun.response import make_succ_empty_response, make_succ_response, make_err_response


@app.route('/')
def index():
    """
    :return: 返回index页面
    """
    return render_template('index.html')


@app.route('/api/count', methods=['POST'])
def count():
    """
    :return:计数结果/清除结果
    """

    # 获取请求体参数
    params = request.get_json()

    # 检查action参数
    if 'action' not in params:
        return make_err_response('缺少action参数')

    # 按照不同的action的值，进行不同的操作
    action = params['action']

    # 执行自增操作
    if action == 'inc':
        counter = query_counterbyid(1)
        if counter is None:
            counter = Counters()
            counter.id = 1
            counter.count = 1
            counter.created_at = datetime.now()
            counter.updated_at = datetime.now()
            insert_counter(counter)
        else:
            counter.id = 1
            counter.count += 1
            counter.updated_at = datetime.now()
            update_counterbyid(counter)
        return make_succ_response(counter.count)

    # 执行清0操作
    elif action == 'clear':
        delete_counterbyid(1)
        return make_succ_empty_response()

    # action参数错误
    else:
        return make_err_response('action参数错误')


@app.route('/api/count', methods=['GET'])
def get_count():
    """
    :return: 计数的值
    """
    counter = Counters.query.filter(Counters.id == 1).first()
    return make_succ_response(0) if counter is None else make_succ_response(counter.count)


@app.route('/api/siliconflow', methods=['POST'])
def silicon_flow_stream():
    """
    流式请求SiliconFlow API
    :return: 流式响应
    """
    try:
        # 从环境变量获取API密钥
        api_key = os.environ.get('SILICONFLOW_KEY')
        if not api_key:
            return make_err_response('未配置SILICONFLOW_KEY环境变量')

        # 获取请求体参数
        payload = request.get_json()
        if not payload:
            return make_err_response('请求体不能为空')

        payload['model'] = 'Qwen/Qwen2-7B-Instruct'
        # 设置SiliconFlow API的URL和请求头
        url = 'https://api.siliconflow.cn/v1/chat/completions'
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {api_key}'
        }

        # 发送流式请求到SiliconFlow API
        def generate():
            # 确保stream参数被设置为True
            if isinstance(payload, dict):
                payload['stream'] = True
            
            with requests.post(url, json=payload, headers=headers, stream=True) as resp:
                if resp.status_code != 200:
                    # 如果状态码不是200，返回错误信息
                    error_msg = f"API请求失败: {resp.status_code} - {resp.text}"
                    yield f"data: {error_msg}\n\n"
                    return
                
                # 逐行返回流式响应
                for line in resp.iter_lines():
                    if line:
                        yield f"data: {line.decode('utf-8')}\n\n"

        # 返回服务器发送事件(SSE)流
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'Connection': 'keep-alive',
                'X-Accel-Buffering': 'no'  # 禁用Nginx的缓冲
            }
        )
    except Exception as e:
        return make_err_response(f'调用SiliconFlow API时发生错误: {str(e)}')
