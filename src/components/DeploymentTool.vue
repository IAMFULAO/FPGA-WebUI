<template>
  <el-card>
    <div slot="header" class="header-with-icon">
      <img src="../assets/header-icon.jpg" class="header-icon">
      <span>大模型 FPGA 部署工具</span>
    </div>

    <el-form label-position="top">
      <!-- 模型选择模块 -->
      <el-form-item label="1. 选择模型">
        <el-select v-model="selectedModel" placeholder="请选择模型">
          <el-option
              v-for="model in models"
              :key="model.value"
              :label="model.label"
              :value="model.value">
            <span style="float: left">{{ model.label }}</span>
            <img :src="model.icon" class="option-icon">
          </el-option>
        </el-select>
      </el-form-item>

      <!-- 量化精度模块 -->
      <el-form-item label="2. 选择量化精度">
        <el-radio-group v-model="selectedQuantPrecision">
          <el-radio v-for="precision in precisions"
                    :label="precision.value"
                    :key="precision.value">
            {{ precision.label }}
          </el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 评分方法 -->
      <el-form-item label="3. 选择评分方法">
        <el-radio-group v-model="selectedEvalMethod">
          <el-radio label="evalPlus">EvalPlus</el-radio>
          <el-radio label="imEvalHarness">ImEvaluationHarness</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 评分对象 -->
      <el-form-item label="4. 选择评分对象">
        <el-radio-group v-model="selectedEvalTarget">
          <el-radio label="origin">原模型</el-radio>
          <el-radio label="quant">量化模型</el-radio>
          <el-radio label="both">两个都评分</el-radio>
          <el-radio label="none">不评分</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- FPGA 部署模块 -->
      <el-form-item class="deploy-section">
        <div class="deploy-button-wrapper">
          <el-button type="primary" @click="startDeploy" :loading="isDeploying">
            <img src="../assets/deploy-icon.jpg" class="button-icon">
            开始部署
          </el-button>

          <el-button
              v-if="isDeploying"
              @click="cancelDeploy"
              style="margin-left: 10px;">
            取消
          </el-button>
        </div>

        <el-alert v-if="deployStatus.length > 0"
                  :title="''"
                  type="info"
                  :closable="false"
                  :show-icon="false"
                  class="status-alert">

          <div class="status-scroll-container">
            <div class="status-text-container">
              <div v-for="(line, index) in deployStatus"
                   :key="index"
                   :class="{
                     'success-line': line.includes('✅'),
                     'error-line': line.includes('❌'),
                     'progress-line': line.includes('-')
                   }">
                {{ line }}
              </div>
            </div>
          </div>
        </el-alert>
      </el-form-item>
    </el-form>
  </el-card>
</template>

<script>
import modelQwen from '../assets/model-qwen.jpg'
import modelDeepseek from '../assets/model-deepseek.jpg'
import axios from 'axios';

export default {
  name: 'DeploymentTool',
  props: {
    authInfo: {
      type: Object,
      required: true
    }
  },
  data() {
    return {
      selectedModel: '',
      selectedQuantPrecision: 'int4',
      isDeploying: false,
      deployStatus: [],
      pollingInterval: null,
      progressPollingInterval: null,
      quantPid: null,
      selectedEvalMethod: 'evalPlus',
      selectedEvalTarget: 'none',
      models: [
        { value: 'qwen2', label: 'Qwen2-7B-Instruct', icon: modelQwen },
        { value: 'qwen2.5', label: 'Qwen2.5-7B-Instruct', icon: modelQwen },
        { value: 'qwen2-vl', label: 'Qwen2-VL-7B-Instruct', icon: modelQwen },
        { value: 'qwen2.5-vl', label: 'Qwen2.5-VL-7B-Instruct', icon: modelQwen },
        { value: 'deepseek', label: 'DeepSeek-R1-Distill-Qwen-7B', icon: modelDeepseek }
      ],
      precisions: [
        { value: 'int2', label: 'INT2', precisionValue: 2 },
        { value: 'int4', label: 'INT4（仅支持）', precisionValue: 4 },
        { value: 'int8', label: 'INT8', precisionValue: 8 }
      ],
      apiUrl: 'http://10.20.108.87:7678/api'
    }
  },
  methods: {
    async startProgressPolling() {
      // 清除已有轮询
      if (this.progressPollingInterval) {
        clearInterval(this.progressPollingInterval);
      }

      this.progressPollingInterval = setInterval(async () => {
        try {
          const response = await axios.get(`${this.apiUrl}/progress`, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (response.data.success) {
            // 更新进度显示
            if (response.data.progress && response.data.progress.length > 0) {
              this.deployStatus = [
                ...this.deployStatus.filter(s => !s.startsWith('-')),
                ...response.data.progress.map(p => `-${p}`)
              ];
            }

            // 检查是否有错误（匹配 ERROR 或异常关键词）
            const hasError = response.data.progress.some(p =>
                p.includes('[ERROR]') ||
                p.includes('异常') ||
                p.includes('失败')
            );

            if (hasError) {
              clearInterval(this.progressPollingInterval);
              this.isDeploying = false;
              this.deployStatus.push('❌ 量化失败，请检查日志');
              this.$message.error('量化过程中发生错误');
              return;
            }

            // 如果量化完成，停止轮询
            if (!response.data.is_running) {
              clearInterval(this.progressPollingInterval);
              this.isDeploying = false;
              this.deployStatus.push('✅ 量化完成');
              this.$emit('deploy-success', {
                name: this.getCurrentModel().label,
                precision: this.getPrecisionName(this.selectedQuantPrecision)
              });
            }
          }
        } catch (error) {
          console.error('获取进度失败:', error);
          clearInterval(this.progressPollingInterval);
          this.isDeploying = false;
          this.deployStatus.push('❌ 无法获取量化进度');
          this.$message.error('量化进度查询失败');
          await this.cancelDeploy();
        }
      }, 3000);
    },

    async startDeploy() {
      if (!this.selectedModel) {
        this.$message.error('请先选择模型');
        return;
      }

      this.isDeploying = true;
      this.deployStatus = [];

      try {
        const model = this.getCurrentModel();

        // 直接启动评估，跳过量化相关步骤
        if (this.selectedEvalTarget !== 'none') {
          this.deployStatus.push('1. 开始评估流程...');
          await this.startEvaluation(this.selectedEvalTarget === 'quant' ? 'quant' : 'origin');
        } else {
          this.$message.warning('未选择评估对象');
        }

      } catch (error) {
        console.error('评估失败:', error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ 评估失败: ${errorMsg}`);
        this.$message.error(`评估失败: ${errorMsg}`);
      } finally {
        this.isDeploying = false;
      }
    },

    async startEvaluation(target) {
      const model = this.getCurrentModel();
      const method = this.selectedEvalMethod;

      this.deployStatus.push(`开始对 ${target === 'origin' ? '原模型' : '量化模型'} 进行评分（方法：${method}）...`);

      try {
        // 修改为正确的API接口和参数格式
        const response = await axios.post(`${this.apiUrl}`, {
          model_name: model.label,
          eval_method: method,
          start_evaluation: true, // 添加评估标志
          is_quantized: target !== 'origin' // 量化判断
        }, {
          headers: {
            'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
          }
        });

        if (response.data.success) {
          this.deployStatus.push(`✅ ${target === 'origin' ? '原模型' : '量化模型'} 评分任务已启动`);
          this.pollEvaluationProgress(target);
        } else {
          throw new Error(response.data.message || '评分启动失败');
        }
      } catch (error) {
        console.error(`评分启动失败 (${target})`, error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分启动失败: ${error.message}`);
      }
    },

    async pollEvaluationProgress(target) {
      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${this.apiUrl}/eval_progress`, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (response.data.success) {
            // 使用后端返回的progress字段而不是logs
            const progressLines = response.data.progress || [];
            this.deployStatus.push(...progressLines.map(log => `📊 ${log}`));

            // 检查评估完成关键词
            const isCompleted = response.data.progress?.some(line =>
                line.includes('评估完成') ||
                line.includes('evaluation completed')
            );

            if (!response.data.is_running || isCompleted) {
              clearInterval(interval);
              const statusMessage = isCompleted ?
                  `✅ ${target === 'origin' ? '原模型' : '量化模型'} 评分完成` :
                  '⚠️ 评估进程已结束但未检测到完成标志';
              this.deployStatus.push(statusMessage);
            }
          }
        } catch (error) {
          clearInterval(interval);
          this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分进度获取失败: ${error.message}`);
        }
      }, 3000);
    },

    async cancelDeploy() {
      if (!this.isDeploying) return;

      this.deployStatus.push('🔴 正在取消评估流程...');

      try {
        const cancelResp = await axios.post(`${this.apiUrl}/cancel_eval`, {}, {
          headers: {
            'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
          }
        });

        cancelResp.data.success
            ? this.deployStatus.push('✅ 已取消评估进程')
            : this.deployStatus.push(`⚠️ 无法取消评估: ${cancelResp.data.message}`);
      } catch (error) {
        this.deployStatus.push(`⚠️ 取消评分失败: ${error.message}`);
      } finally {
        this.isDeploying = false;
      }
    },

    async sendDeployRequest(data) {
      try {
        const authHeader = 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`);

        const response = await axios.post(this.apiUrl, data, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader
          }
        })

        if (response.status !== 200) {
          const error = new Error(response.data.message || '服务器返回错误');
          this.$reportError(error, {
            action: 'api_request',
            requestData: JSON.stringify(data),
            responseStatus: response.status,
            responseData: JSON.stringify(response.data)
          });
          throw error;
        }

        return response.data;
      } catch (error) {
        this.$reportError(error, {
          action: 'api_request',
          requestData: JSON.stringify(data),
          isAxiosError: error.isAxiosError,
          responseStatus: error.response?.status
        });
        throw new Error(`API请求失败: ${error.message}`);
      }
    },

    delay(ms) {
      return new Promise(resolve => setTimeout(resolve, ms));
    },

    getCurrentModel() {
      return this.models.find(m => m.value === this.selectedModel);
    },

    getModelName(value) {
      const model = this.models.find(m => m.value === value);
      return model ? model.label : '';
    },

    getPrecisionName(value) {
      const precision = this.precisions.find(p => p.value === value);
      return precision ? precision.label.toUpperCase() : '';
    }
  },

  beforeDestroy() {
    if (this.progressPollingInterval) {
      clearInterval(this.progressPollingInterval);
    }
    if (this.pollingInterval) {
      clearInterval(this.pollingInterval);
    }
  }
}
</script>

<style scoped>

.deployment-tool-card {
  width: 100%;
  min-height: 700px; /* 增加最小高度 */
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.header-with-icon {
  display: flex;
  align-items: center;
  justify-content: center; /* 添加水平居中 */
  font-size: 20px;
  font-weight: bold;
  width: 100%; /* 确保宽度填满 */
  text-align: center; /* 作为备用方案 */
}

.header-icon {
  width: 32px;
  height: 32px;
  margin-right: 10px;
}

.option-icon {
  width: 20px;
  height: 20px;
  float: right;
  margin-top: 2px;
}

.radio-icon {
  width: 16px;
  height: 16px;
  vertical-align: middle;
  margin-right: 5px;
}

.button-icon {
  width: 18px;
  height: 18px;
  vertical-align: middle;
  margin-right: 5px;
}

.el-card {
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
}

::v-deep .el-form-item__label {
  font-size: 16px;
  font-weight: bold;
  color: #333;
}

/* 修改后的样式 */
.deploy-section {
  margin-top: 20px;
  display: flex;
  flex-direction: column;
  align-items: center; /* 使子元素水平居中 */
}

.deploy-button-wrapper {
  width: 100%; /* 确保容器宽度足够 */
  display: flex;
  justify-content: center;
  margin-bottom: 20px;
}

/* 修复 el-form-item 的默认样式影响 */
.el-form-item__content {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.status-alert {
  margin-top: 10px;
  width: 100%;
  max-width: 800px;
  box-sizing: border-box;
}

.status-scroll-container {
  max-height: 400px;
  overflow-y: auto;
  overflow-x: hidden;
  width: 100%;
  background-color: transparent;
  border: none;
  border-radius: 0;
  box-sizing: border-box;
  padding-right: 0;
  min-width: 0;
}

.status-text-container {
  width: 760px;
  overflow-x: auto;
  overflow-y: hidden;
  padding: 10px;
  word-break: break-word;
  box-sizing: border-box;
  min-width: 0;
}

.success-line {
  color: #67C23A;
  font-weight: bold;
}

.error-line {
  color: #F56C6C;
  font-weight: bold;
}

.progress-line {
  color: #409EFF;
}
</style>