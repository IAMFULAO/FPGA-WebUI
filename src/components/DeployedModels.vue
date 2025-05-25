<template>
  <el-card class="deployed-models-card">
    <div slot="header" class="header-with-icon">
      <span>已部署模型</span>
    </div>

    <div v-if="models.length === 0" class="empty-message">
      暂无已部署模型
    </div>

    <div v-else class="model-list">
      <div v-for="(model, index) in models" :key="index" class="model-item">
        <div class="model-info">
          <div class="model-name">{{ model.model_name || '默认模型' }}</div>
          <div class="model-precision">量化精度: {{ model.precision || 4 }}</div>
          <div class="model-time">部署时间: {{ formatTime(model.time) }}</div>
        </div>
        <el-button
            size="mini"
            type="danger"
            @click="handleRemoveModel(index)"
            class="remove-btn">
          移除
        </el-button>
      </div>
    </div>
  </el-card>
</template>

<script>
import { ref, onMounted } from 'vue'
import axios from 'axios'

export default {
  name: 'DeployedModels',
  props: {
    models: {
      type: Array,
      default: () => []
    },
    authInfo: {
      type: Object,
      default: () => ({ username: '', password: '' })
    }
  },
  emits: ['remove'],
  setup(props, { emit }) {
    const formatTime = (timestamp) => {
      if (!timestamp) {
        timestamp = new Date().getTime()
      }
      return new Date(timestamp).toLocaleString()
    }

    const fetchQuantizationParams = async () => {
      try {
        const authHeader = 'Basic ' + btoa(`${props.authInfo.username}:${props.authInfo.password}`)
        const response = await axios.post('http://10.20.108.87:7678/api', {
          action: "get_quantization_params"
        }, {
          headers: {
            'Content-Type': 'application/json',
            'Authorization': authHeader
          }
        })

        if (response.data) {
          const modelData = {
            ...response.data,
            time: new Date().getTime()
          }

          const exists = props.models.some(
              m => m.model_name === modelData.model_name &&
                  m.precision === modelData.precision
          )

          if (!exists && modelData.model_name) {
            emit('add-model', modelData)
          }
        }
      } catch (error) {
        if (error.response?.status === 401) {
          console.error('认证过期，请重新登录')
        }
        console.error('获取量化参数失败:', error)
        // 上报错误
        if (window.$vueApp && window.$vueApp.config.globalProperties.$reportError) {
          window.$vueApp.config.globalProperties.$reportError(error, {
            action: 'fetch_quantization_params',
            endpoint: 'http://10.20.108.87:7678/api'
          })
        }
      }
    }

    const handleRemoveModel = (index) => {
      try {
        emit('remove', index)
      } catch (error) {
        console.error('移除模型失败:', error)
        // 上报错误
        if (window.$vueApp && window.$vueApp.config.globalProperties.$reportError) {
          window.$vueApp.config.globalProperties.$reportError(error, {
            action: 'remove_model',
            modelIndex: index,
            modelsCount: props.models.length
          })
        }
      }
    }

    onMounted(() => {
      fetchQuantizationParams()
      setInterval(fetchQuantizationParams, 5000)
    })

    return {
      formatTime,
      handleRemoveModel
    }
  }
}
</script>

<style scoped>
.deployed-models-card {
  height: fit-content;
  margin-left: 20px;
}

.header-with-icon {
  font-size: 18px;
  font-weight: bold;
}

.model-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.model-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px;
  background: #f9f9f9;
  border-radius: 4px;
}

.model-info {
  flex: 1;
}

.model-name {
  font-weight: bold;
  margin-bottom: 4px;
}

.model-precision, .model-time {
  font-size: 12px;
  color: #666;
}

.empty-message {
  color: #999;
  text-align: center;
  padding: 20px;
}
</style>