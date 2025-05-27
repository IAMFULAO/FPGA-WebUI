<template>
  <div id="app">
    <Login v-if="!isLoggedIn" @login-success="handleLoginSuccess" />
    <div v-else class="container">
      <div class="top-section">
        <DeploymentTool
            ref="deploymentTool"
            @deploy-success="handleDeploySuccess"
            @quant-log="handleQuantLog"
            @eval-log="handleEvalLog"
            :deployed-models="deployedModels"
            :auth-info="authInfo" />

        <div class="log-displays">
          <QuantLogDisplay :logs="quantLogs" />
          <EvalLogDisplay :logs="evalLogs" />
        </div>
      </div>

      <div class="bottom-section">
        <DeployedModels
            :models="deployedModels"
            @remove="removeModel"
            :auth-info="authInfo" />
        <div class="image-section">
          <MyImage />
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import Login from './components/Login.vue'
import DeploymentTool from './components/DeploymentTool.vue'
import MyImage from './components/MyImage.vue'
import DeployedModels from './components/DeployedModels.vue'
import QuantLogDisplay from './components/QuantLogDisplay.vue'
import EvalLogDisplay from './components/EvalLogDisplay.vue'

export default {
  name: 'App',
  components: {
    Login,
    DeploymentTool,
    MyImage,
    DeployedModels,
    QuantLogDisplay,
    EvalLogDisplay
  },
  data() {
    return {
      isLoggedIn: false,
      authInfo: {},
      deployedModels: [],
      quantLogs: [],
      evalLogs: []
    }
  },
  methods: {
    handleLoginSuccess(credentials) {
      this.authInfo = credentials
      this.isLoggedIn = true
    },

    handleQuantLog(newLogs) {
      console.log('收到量化日志:', newLogs)
      const lastLength = this.quantLogs.length
      const overlap = newLogs.slice(0, lastLength).every((line, i) => line === this.quantLogs[i])
      if (overlap) {
        this.quantLogs = [...this.quantLogs, ...newLogs.slice(lastLength)]
      } else {
        this.quantLogs = [...new Set([...this.quantLogs, ...newLogs])]
      }
    },

    handleEvalLog(newLogs) {
      console.log('收到评估日志:', newLogs)
      const lastLength = this.evalLogs.length
      const overlap = newLogs.slice(0, lastLength).every((line, i) => line === this.evalLogs[i])
      if (overlap) {
        this.evalLogs = [...this.evalLogs, ...newLogs.slice(lastLength)]
      } else {
        this.evalLogs = [...new Set([...this.evalLogs, ...newLogs])]
      }
    },

    handleDeploySuccess(modelData) {
      try {
        this.quantLogs = []
        this.evalLogs = []

        this.deployedModels.push({
          name: modelData.name,
          precision: modelData.precision,
          time: new Date().toLocaleString()
        })
      } catch (err) {
        this.$reportError(err, {
          action: 'handle_deploy_success',
          modelData: JSON.stringify(modelData)
        })
        this.$message.error('部署记录保存失败')
      }
    },
    removeModel(index) {
      try {
        this.deployedModels.splice(index, 1)
        this.$message.success('模型已移除')
      } catch (err) {
        this.$reportError(err, {
          action: 'remove_model',
          index: index
        })
        this.$message.error('模型移除失败')
      }
    },
    globalErrorHandler(err, vm, info) {
      this.$reportError(err, {
        component: vm?.$options?.name,
        lifecycleHook: info,
        stack: err.stack
      })
      console.error('全局捕获的错误:', err)
    }
  },
  mounted() {
    // 注册未处理的Promise rejection
    window._unhandledRejection = (event) => {
      this.$reportError(event.reason, {
        type: 'unhandled_rejection'
      })
    }
    window.addEventListener('unhandledrejection', window._unhandledRejection)
  },
  beforeUnmount() {
    if (window._unhandledRejection) {
      window.removeEventListener('unhandledrejection', window._unhandledRejection)
    }
  }
}
</script>

<style>
body {
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", Arial, sans-serif;
  margin: 0;
  padding: 20px;
  background-color: #f5f7fa;
}

.container {
  max-width: 95%;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.top-section {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.log-displays {
  flex: 1;
  min-width: 300px;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.bottom-section {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.dashboard {
  display: flex;
  gap: 20px;
  flex-wrap: wrap;
}

.dashboard > *:first-child {
  flex: 2;
  min-width: 800px;
}

.dashboard > *:last-child {
  flex: 1;
  min-width: 300px;
}

.image-section {
  display: flex;
  justify-content: center;
}
</style>