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
          <el-radio label="lmEvalHarness">lmEvaluationHarness</el-radio>
        </el-radio-group>
      </el-form-item>

      <!-- 评估任务选择 -->
      <el-form-item label="4. 选择评估任务" v-if="selectedEvalMethod && selectedEvalTarget !== 'none'">
        <el-checkbox-group v-model="selectedEvalTasks">
          <el-checkbox
              v-for="task in getAvailableTasks()"
              :key="task.value"
              :label="task.value">
            {{ task.label }}
          </el-checkbox>
        </el-checkbox-group>
      </el-form-item>

      <!-- 评分对象 -->
      <el-form-item label="5. 选择评分对象">
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
      quantLogs: [],
      evalLogs:[],
      dataLogs:[],
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
      evalPlusTasks: [
        { value: 'humaneval', label: 'HumanEval' },
        { value: 'mbpp', label: 'MBPP' }
      ],
      lmEvalHarnessTasks: [
        { value: 'arc_easy', label: 'ARC Easy' },
        { value: 'arc_challenge', label: 'ARC Challenge' },
        { value: 'gsm8k_cot', label: 'GSM8K CoT' },
        { value: 'gsm8k_platinum_cot', label: 'GSM8K Platinum CoT' },
        { value: 'hellaswag', label: 'HellaSwag' },
        { value: 'mmlu', label: 'MMLU' },
        { value: 'gpqa', label: 'GPQA' },
        { value: 'boolq', label: 'BoolQ' },
        { value: 'openbookqa', label: 'OpenBookQA' }
      ],
      selectedEvalTasks: [],
      apiUrl: 'http://10.20.108.87:7678/api'
    }
  },
  methods: {
    getAvailableTasks() {
      return this.selectedEvalMethod === 'evalPlus'
          ? this.evalPlusTasks
          : this.lmEvalHarnessTasks;
    },

    async startProgressPolling() {
      // 清除已有轮询
      if (this.progressPollingInterval) {
        clearInterval(this.progressPollingInterval);
      }

      let failCount = 0;
      const MAX_FAILS = 5;

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
              const logs = response.data.progress || [];
              this.quantLogs.push(...logs);
              this.$emit('quant-log', response.data.progress);
              failCount = 0;
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

            const hasCompleted = this.quantLogs.some(line =>
                line.includes('量化完成') ||
                line.includes('完成') ||
                line.toLowerCase().includes('quantization finished') ||
                line.toLowerCase().includes('success')
            );

            if (!response.data.is_running && !hasCompleted) {
              clearInterval(this.progressPollingInterval);
              this.isDeploying = false;
              this.deployStatus.push('❌ 量化进程结束但未检测到“完成”，可能失败');
              return;
            }

            if (hasCompleted) {
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
          const errMsg = error?.message || '';
          const isAxiosError = error.isAxiosError === true;
          const noResponse = !error.response;

          const isIgnorable =
              errMsg.includes('ERR_EMPTY_RESPONSE') ||
              (isAxiosError && noResponse);

          if (isIgnorable) {
            failCount++;
            console.warn(`⚠️ 量化进度轮询失败（可忽略）: ${errMsg}，已失败 ${failCount} 次`);

            if (failCount >= MAX_FAILS) {
              clearInterval(this.progressPollingInterval);
              this.isDeploying = false;
              this.deployStatus.push('❌ 连续多次无法获取量化进度，任务可能失败');
              this.$message.error('连续多次进度查询失败');
              await this.cancelDeploy();
            }
            return;
          }
          clearInterval(this.progressPollingInterval);
          this.isDeploying = false;
          this.deployStatus.push(`❌ 无法获取量化进度: ${errMsg}`);
          this.$message.error('量化进度查询失败');
          await this.cancelDeploy();
        }
      }, 3000);
    },

    async startEvaluationPolling(target) {
      let failCount = 0;
      const MAX_FAILS = 5;

      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${this.apiUrl}/eval_progress`, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (response.data.success) {
            failCount = 0;
            const progressLines = response.data.progress || [];
            this.evalLogs.push(...progressLines);
            this.$emit('eval-log', progressLines);

            const hasError = this.evalLogs.some(line =>
                line.includes('[ERROR]') ||
                line.includes('失败') ||
                line.includes('异常') ||
                line.includes('Traceback')
            );

            const hasCompleted = this.evalLogs.some(line =>
                line.includes('完成') ||
                line.toLowerCase().includes('evaluation finished') ||
                line.toLowerCase().includes('scoring complete') ||
                line.toLowerCase().includes('done')
            );

            if (hasError) {
              clearInterval(interval);
              this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分失败，请检查日志`);
              return;
            }

            if (!response.data.is_running && !hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分中断但未检测到“完成”关键词，可能失败`);
              return;
            }

            if (hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`✅ ${target === 'origin' ? '原模型' : '量化模型'} 评分完成`);
            }
          }
        } catch (error) {
          const isAxiosError = error.isAxiosError;
          const errMsg = error?.message || '';
          const isIgnorable = errMsg.includes('ERR_EMPTY_RESPONSE') ||
              (isAxiosError && !error.response);

          if (isIgnorable) {
            failCount++;
            console.warn(`⚠️ 评分轮询失败（可忽略）: ${errMsg}，当前失败次数: ${failCount}`);

            if (failCount >= MAX_FAILS) {
              clearInterval(interval);
              this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 连续多次无法获取评分进度，任务可能失败`);
              this.$message.error('评分进度查询连续失败，已中止');
            }
            return;
          }
          clearInterval(interval);
          this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分进度获取失败: ${errMsg}`);
          this.$message.error('评分进度查询失败');
        }
      }, 3000);
    },

    async startDeploymentPolling() {
      let failCount = 0;
      const MAX_FAILS = 5;

      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${this.apiUrl}/deploy_progress`, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (response.data.success) {
            failCount = 0;
            const progressLines = response.data.logs || [];
            this.deployLogs.push(...progressLines);
            this.$emit('deploy-log', progressLines);

            const hasError = this.deployLogs.some(line =>
                line.includes('[ERROR]') ||
                line.includes('失败') ||
                line.includes('异常') ||
                line.includes('Traceback')
            );

            const hasCompleted = this.deployLogs.some(line =>
                line.includes('完成') ||
                line.toLowerCase().includes('deployment finished') ||
                line.toLowerCase().includes('done')
            );

            if (hasError) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 模型部署失败，请检查日志`);
              return;
            }

            if (!response.data.is_running && !hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 模型部署中断但未检测到“完成”关键词，可能失败`);
              return;
            }

            if (hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`✅ 模型部署完成`);
            }
          }
        } catch (error) {
          const isAxiosError = error.isAxiosError;
          const errMsg = error?.message || '';
          const isIgnorable = errMsg.includes('ERR_EMPTY_RESPONSE') ||
              (isAxiosError && !error.response);

          if (isIgnorable) {
            failCount++;
            console.warn(`⚠️ 部署轮询失败（可忽略）: ${errMsg}，当前失败次数: ${failCount}`);

            if (failCount >= MAX_FAILS) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 连续多次无法获取部署进度，任务可能失败`);
              this.$message.error('部署进度查询连续失败，已中止');
            }
            return;
          }

          clearInterval(interval);
          this.deployStatus.push(`❌ 部署进度获取失败: ${errMsg}`);
          this.$message.error('部署进度查询失败');
        }
      }, 3000);
    },

    async startCompilationPolling() {
      let failCount = 0;
      const MAX_FAILS = 5;

      const interval = setInterval(async () => {
        try {
          const response = await axios.get(`${this.apiUrl}/compile_progress`, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (response.data.success) {
            failCount = 0;
            const progressLines = response.data.progress || [];
            this.compileLogs.push(...progressLines);
            this.$emit('compile-log', progressLines);  // 向父组件分发日志事件

            const hasError = this.compileLogs.some(line =>
                line.includes('[ERROR]') ||
                line.includes('失败') ||
                line.includes('异常') ||
                line.includes('Traceback')
            );

            const hasCompleted = this.compileLogs.some(line =>
                line.includes('完成') ||
                line.toLowerCase().includes('compile finished') ||
                line.toLowerCase().includes('compilation complete') ||
                line.toLowerCase().includes('done')
            );

            if (hasError) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 模型编译失败，请检查日志`);
              return;
            }

            if (!response.data.is_running && !hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 模型编译中断但未检测到“完成”关键词，可能失败`);
              return;
            }

            if (hasCompleted) {
              clearInterval(interval);
              this.deployStatus.push(`✅ 模型编译完成`);
            }
          }
        } catch (error) {
          const isAxiosError = error.isAxiosError;
          const errMsg = error?.message || '';
          const isIgnorable = errMsg.includes('ERR_EMPTY_RESPONSE') ||
              (isAxiosError && !error.response);

          if (isIgnorable) {
            failCount++;
            console.warn(`⚠️ 编译轮询失败（可忽略）: ${errMsg}，当前失败次数: ${failCount}`);

            if (failCount >= MAX_FAILS) {
              clearInterval(interval);
              this.deployStatus.push(`❌ 连续多次无法获取编译进度，任务可能失败`);
              this.$message.error('编译进度查询连续失败，已中止');
            }
            return;
          }

          clearInterval(interval);
          this.deployStatus.push(`❌ 编译进度获取失败: ${errMsg}`);
          this.$message.error('编译进度查询失败');
        }
      }, 3000);
    },

    async startDeploy() {
      if (!this.selectedModel) {
        this.$message.error('请先选择模型');
        return;
      }

      this.quantLogs = [];
      this.evalLogs = [];
      this.deployLogs = [];
      this.deployStatus = [];

      this.$emit('quant-log', []);
      this.$emit('eval-log', []);
      this.$emit('deploy-log', []);

      this.isDeploying = true;

      try {
        const model = this.getCurrentModel();
        const precision = this.precisions.find(p => p.value === this.selectedQuantPrecision);

        const requestData = {
          model_name: model.label,
          precision: precision.precisionValue
        };

        // 1. 调用API发送部署请求
        this.deployStatus.push('1. 正在发送部署请求到服务器...');
        await this.sendDeployRequest(requestData);
        this.deployStatus.push('服务器已接收部署请求');

        if (this.selectedEvalTarget === 'origin' || this.selectedEvalTarget === 'both') {
          this.startEvaluation('origin');
        }

        // 2. 量化处理
        this.deployStatus.push(`2. 量化中 (${this.getPrecisionName(this.selectedQuantPrecision)})...`);
        const quantResponse = await this.sendDeployRequest({
          model_name: model.label,
          start_quantization: true
        });

        // 检查量化是否成功启动
        if (quantResponse.message && quantResponse.message.includes('量化进程已启动')) {
          this.deployStatus.push('量化开始');
        } else {
          throw new Error('量化启动失败');
        }

        if (quantResponse.success && quantResponse.pid) {
          this.quantPid = quantResponse.pid;
          this.deployStatus.push(`2. 量化中 (PID: ${this.quantPid})...`);

          // 开始轮询进度
          this.startProgressPolling();
        } else {
          throw new Error(quantResponse.message || '量化启动失败');
        }

        const hasFinished = this.deployStatus.some(line => line.includes('✅ 量化完成'));

        if (this.selectedEvalTarget === 'quant' || this.selectedEvalTarget === 'both') {
          this.deployStatus.push('等待量化完成后对量化模型进行评分...');
          const checkQuantCompletion = setInterval(() => {
            if (hasFinished) {
              clearInterval(checkQuantCompletion);
              this.startEvaluation('quant');
            }
          }, 3000);
        }

        if (hasFinished) {
          this.startDeployment();
          this.startCompilation();
        }

        // 4. 完成
        this.deployStatus.push('✅ 部署成功！');
        this.$emit('deploy-success', {
          name: model.label,
          precision: this.getPrecisionName(this.selectedQuantPrecision)
        });

      } catch (error) {
        console.error('部署失败:', error);
        const errorMsg = error.response?.data?.message || error.message;

        this.$reportError(error, {
          action: 'model_deployment',
          model: this.selectedModel,
          precision: this.selectedQuantPrecision,
          errorMsg: errorMsg,
          status: this.deployStatus.join('\n')
        });

        if (errorMsg.includes('量化启动失败')) {
          this.deployStatus.push('❌ 量化失败: 无法启动量化进程');
        } else {
          this.deployStatus.push(`❌ 部署失败: ${errorMsg}`);
        }

        this.$message.error(`部署失败: ${errorMsg}`);
        if (this.progressPollingInterval) {
          clearInterval(this.progressPollingInterval);
        }
        await this.cancelDeploy();
      } finally {
      }
    },

    async startEvaluation(target) {
      const model = this.getCurrentModel();
      const method = this.selectedEvalMethod;

      this.evalLogs = [];
      this.deployStatus.push(`开始对 ${target === 'origin' ? '原模型' : '量化模型'} 进行评分（方法：${method}）...`);

      try {
        // 修改为正确的API接口和参数格式
        const response = await axios.post(`${this.apiUrl}`, {
          model_name: model.label,
          eval_method: method,
          eval_tasks: this.selectedEvalTasks, // 新增
          start_evaluation: true,
          is_quantized: target !== 'origin'
        }, {
          headers: {
            'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
          }
        });

        if (response.data.success) {
          this.deployStatus.push(`✅ ${target === 'origin' ? '原模型' : '量化模型'} 评分任务已启动`);
          this.startEvaluationPolling(target);
        } else {
          throw new Error(response.data.message || '评分启动失败');
        }
      } catch (error) {
        console.error(`评分启动失败 (${target})`, error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ ${target === 'origin' ? '原模型' : '量化模型'} 评分启动失败: ${error.message}`);
      }
    },

    async startDeployment() {
      const model = this.getCurrentModel();

      this.deployLogs = [];
      this.deployStatus.push(`开始部署模型 ${model.label} ...`);

      try {
        const response = await axios.post(`${this.apiUrl}`, {
          model_name: model.label,
          start_deployment: true
        }, {
          headers: {
            'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
          }
        });

        if (response.data.success) {
          this.deployStatus.push(`✅ 模型 ${model.label} 部署任务已启动 (PID: ${response.data.pid})`);
          this.startDeploymentPolling();  // 轮询日志或状态
        } else {
          throw new Error(response.data.message || '部署启动失败');
        }
      } catch (error) {
        console.error('部署启动失败', error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ 模型 ${model.label} 部署启动失败: ${errorMsg}`);
      }
    },

    async startCompilation() {
      const model = this.getCurrentModel();
      this.compileLogs = [];
      this.deployStatus.push(`开始对模型 ${model.label} 进行编译...`);

      try {
        const response = await axios.post(`${this.apiUrl}`, {
          model_name: model.label,
          start_compilation: true
        }, {
          headers: {
            'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
          }
        });

        if (response.data.success) {
          this.deployStatus.push(`✅ 模型 ${model.label} 编译任务已启动`);
          this.startCompilationPolling();  // 轮询编译日志
        } else {
          throw new Error(response.data.message || '编译启动失败');
        }
      } catch (error) {
        console.error("编译启动失败", error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ 编译启动失败: ${errorMsg}`);
      }
    },


    async cancelDeploy() {
      try {
        if (!this.isDeploying) return;

        // 1. 停止前端轮询（包括量化进度）
        if (this.progressPollingInterval) {
          clearInterval(this.progressPollingInterval);
        }

        this.deployStatus.push('🔴 正在取消部署流程...');

        // 2. 取消量化进程
        try {
          const quantCancelResp = await axios.post(`${this.apiUrl}/cancel_quant`, {}, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (quantCancelResp.data.success) {
            this.deployStatus.push('✅ 已成功取消量化进程');
          } else {
            this.deployStatus.push('⚠️ 取消量化失败: ' + quantCancelResp.data.message);
          }
        } catch (e) {
          this.deployStatus.push('⚠️ 取消量化时发生异常: ' + (e.message || '未知错误'));
        }

        // 3. 取消评分进程（无论是否启动）
        try {
          const cancelResp = await axios.post(`${this.apiUrl}/cancel_eval`, {}, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (cancelResp.data.success) {
            this.deployStatus.push(`✅ 已取消评估进程`);
          } else {
            this.deployStatus.push(`⚠️ 无法取消评估: ${cancelResp.data.message}`);
          }
        } catch (error) {
          this.deployStatus.push(`⚠️ 取消评分失败: ${error.message}`);
        }

        // 取消部署
        try {
          const cancelResp = await axios.post(`${this.apiUrl}/cancel_deployment`, {}, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (cancelResp.data.success) {
            this.deployStatus.push(`✅ 已取消部署进程`);
            this.$message.success('部署进程已成功取消');
          } else {
            this.deployStatus.push(`⚠️ 无法取消部署: ${cancelResp.data.message}`);
            this.$message.warning(cancelResp.data.message || '无法取消部署进程');
          }
        } catch (error) {
          const errMsg = error?.response?.data?.message || error.message;
          this.deployStatus.push(`❌ 取消部署失败: ${errMsg}`);
          this.$message.error('取消部署失败');
        }

        try {
          const cancelResp = await axios.post(`${this.apiUrl}/cancel_compile`, {}, {
            headers: {
              'Authorization': 'Basic ' + btoa(`${this.authInfo.username}:${this.authInfo.password}`)
            }
          });

          if (cancelResp.data.success) {
            this.deployStatus.push(`✅ 已取消编译进程`);
          } else {
            this.deployStatus.push(`⚠️ 无法取消编译: ${cancelResp.data.message}`);
          }
        } catch (error) {
          this.deployStatus.push(`⚠️ 取消编译失败: ${error.message}`);
        }

        // 4. 状态重置
        this.isDeploying = false;
        this.$message.warning('部署流程和评分流程已中断');

      } catch (error) {
        console.error('取消部署失败:', error);
        const errorMsg = error.response?.data?.message || error.message;
        this.deployStatus.push(`❌ 取消失败: ${errorMsg}`);
        this.$message.error(`取消失败: ${errorMsg}`);
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

  watch: {
    selectedEvalMethod() {
      this.selectedEvalTasks = []; // 切换评估框架时清空已选任务
    },
    selectedEvalTarget(newVal) {
      if (newVal === 'none') {
        this.selectedEvalTasks = []; // 选择"不评分"时清空已选任务
      }
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