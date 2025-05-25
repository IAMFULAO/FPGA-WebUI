from flask import Flask, request, jsonify
from flask_cors import CORS

# 创建Flask应用
app = Flask(__name__)

# 启用跨域支持(CORS)
CORS(app)

# 存储量化参数的全局变量
quantization_params = {
    "model_name": None,
    "precision": 4  # 默认精度
}

# GET /api 路由 - 用于浏览器直接访问
@app.route('/api', methods=['GET'])
def get_api():
    return '''
    <h1>API 服务已运行</h1>
    <p>这是 GET /api 的响应</p>
    <p>当前量化参数:</p>
    <ul>
      <li>模型: {}</li>
      <li>精度: {}</li>
    </ul>
    <p>你可以：</p>
    <ul>
      <li>用 Postman 发送 POST 请求到 /api 设置参数</li>
      <li>或者在前端代码中调用这个 API</li>
    </ul>
    '''.format(quantization_params["model_name"] or "默认模型", 
               quantization_params["precision"])

# POST /api 路由 - 接收前端数据
@app.route('/api', methods=['POST'])
def post_api():
    global quantization_params
    
    data = request.get_json()
    print('收到 POST 请求数据:', data)
    
    # 处理获取参数的请求
    if data.get("action") == "get_quantization_params":
        return jsonify(quantization_params)
    
    # 处理设置参数的请求
    if "model_name" in data:
        quantization_params["model_name"] = data["model_name"]
    if "precision" in data:
        quantization_params["precision"] = int(data["precision"])
    
    return jsonify({
        'success': True,
        'message': '参数更新成功',
        'current_params': quantization_params
    })

# 启动服务器
if __name__ == '__main__':
    PORT = 3000
    print(f'''
    服务器已启动！
    - GET 测试: http://localhost:{PORT}/api
    - POST 测试需使用 Postman 或前端调用
    ''')
    app.run(port=PORT)